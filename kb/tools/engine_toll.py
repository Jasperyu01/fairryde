"""Reference evaluation of PB-FC-TOLL (ERP disputes) on an organizer-format case such as round 1 case E11 and its variants.

Purpose: make the ERP rules testable the way engine_noshow.py does for the no-show fee: FC-R06 (the rider's share) first, then
FC-F04 (expected ERP), FC-R07 (ERP overstated), FC-F03 and FC-R08 (ERP caused by an unjustified detour), and FC-R01 (which sends
detour ERP to its own FC-TOLL claim). It is a verification tool for the knowledge base, not the product engine:
- there is no LLM: the READ part of FC-F03 (is the detour justified?) is an input of the case (route_review.justification),
  and the run-agreement and rules-engine confidence terms of AUTH-05 are not computed, so tier AUTO here means that no
  approval trigger fired, before the confidence test;
- only the rules named above are applied (no MAT, DQ, META-02 date check or FC-R12 beyond missing gantry data).
Case fields read: trip_data.service_type, trip_data.carpool, trip_data.fare_type, trip_data.quoted_fare,
fare_breakdown.erp_toll (the ERP line the rider was charged) and base_fare, erp_charges.gantry_passes (timestamp, gantry,
active, rate_sgd), route_review.recommended_gantries (the gantries of the recommended route) and route_review.justification.
"""
from __future__ import annotations

from kbload import KB

PROFILE = "ryde_2026"       # ERP parameters are shared; the profile only supplies AUTO_LIMIT_SGD through the shared fallback


def _r2(x: float) -> float:
    return round(x + 1e-9, 2)


def rider_share(kb: KB, case: dict) -> tuple[float | None, str, list[str]]:
    """FC-R06: (share, basis, kinds). None when Ryde's articles give no order (RydeSEND and carpool at once)."""
    trip = case.get("trip_data", {})
    service = kb.resolve("TX-SERVICE", trip.get("service_type"))
    kinds = []
    if service == "RYDESEND":
        kinds.append("RYDESEND")
    if service == "CARPOOL" or trip.get("carpool"):
        kinds.append("CARPOOL")
    table = kb.tables["ERP_RIDER_SHARE"]["value"]
    if len(kinds) > 1:
        return None, "RydeSEND and carpool at once: no order in Ryde's articles", kinds
    if kinds:
        return float(table[kinds[0]]), f"FC-R06 {kinds[0]}", kinds
    return float(table["default"]), "FC-R06 default (the rider pays the ERP)", kinds


def gantry_rate(kb: KB, g: dict) -> float | None:
    """The rate in the trip's own gantry log, else the LTA table row for that gantry and time of day."""
    if g.get("rate_sgd") is not None:
        return float(g["rate_sgd"])
    hhmm = (g.get("timestamp") or "")[11:16]
    for row in kb.tables["ERP_RATE_TABLE"]["rows"]:
        lo, hi = row["window"].split("-")
        if row["gantry"].lower() == (g.get("gantry") or "").lower() and lo <= hhmm <= hi:
            return float(row["rate_sgd"])
    return None


def erp_of(kb: KB, gantries: list[dict], share: float) -> float | None:
    """FC-F04: the rider's share times the rates of the active gantries on a path (None if a rate is unknown)."""
    total = 0.0
    for g in gantries:
        if g.get("active", True) is False:
            continue
        r = gantry_rate(kb, g)
        if r is None:
            return None
        total += r
    return _r2(share * total)


def run(kb: KB, case: dict) -> dict:
    trip, fare = case.get("trip_data", {}), case.get("fare_breakdown", {})
    steps, flags, reasons, fraud, triggers, decisive, attach = [], [], [], [], [], [], {}
    out = {"steps": steps, "flags": flags, "reasons": reasons, "fraud": fraud, "attach": attach, "amount": None}

    def finish(outcome, amount=None):
        limit = kb.pval("AUTO_LIMIT_SGD", PROFILE)
        if outcome != "ESCALATE_HUMAN" and amount is not None and amount > limit:
            triggers.append(f"amount S${amount:.2f} above AUTO_LIMIT_SGD S${limit:.2f}")
        tier = "HUMAN" if outcome == "ESCALATE_HUMAN" else ("APPROVE" if triggers or decisive else "AUTO")
        out.update(outcome=outcome, amount=amount, tier=tier, triggers=triggers, decisive=decisive)
        return out

    share, basis, kinds = rider_share(kb, case)                                                       # PB-FC-TOLL 1: FC-R06
    steps.append(("FC-R06", f"share {share}: {basis}"))
    if share is None:
        reasons.append("GEN-R-POLICY-GAP")
        steps.append(("GEN-R07", "no rule orders RydeSEND and carpool"))
        return finish("ESCALATE_HUMAN")
    gantries = (case.get("erp_charges") or {}).get("gantry_passes")
    charged = fare.get("erp_toll")
    actual = erp_of(kb, gantries, share) if gantries is not None else None                           # PB-FC-TOLL 2: FC-F04
    if actual is None or charged is None:
        reasons.append("FC-R-INSUFFICIENT-DATA")
        steps.append(("FC-R12", "no gantry log, a gantry without a rate, or no ERP line charged"))
        return finish("ESCALATE_HUMAN")
    charged = _r2(float(charged))
    steps.append(("FC-F04", f"expected ERP {actual:.2f} for the rider (charged {charged:.2f})"))
    out["expected"] = actual
    tol_lo, tol_hi = kb.param("TOLL_TOLERANCE_SGD", PROFILE)["plausible_range"]
    tol = kb.pval("TOLL_TOLERANCE_SGD", PROFILE)
    over = _r2(charged - actual) if charged - actual > tol + 1e-9 else 0.0                              # PB-FC-TOLL 3: FC-R07
    if over:
        reasons.append("FC-R-TOLL-OVERSTATED")
        fraud.append("DRIVER")
        flags.append("FRAUD_SIGNAL")
        triggers.append("fraud signal on DRIVER (ERP overstated, FC-R07)")
        steps.append(("FC-R07", f"ERP overstated by {over:.2f}"))
    if (charged - actual > tol_lo + 1e-9) != (charged - actual > tol_hi + 1e-9):
        decisive.append(("TOLL_TOLERANCE_SGD", f"the outcome changes when the tolerance moves within [{tol_lo}, {tol_hi}]"))
    detour = 0.0                                                                                      # PB-FC-TOLL 4 and 5: FC-F03, FC-R08
    review = case.get("route_review") or {}
    if review.get("recommended_gantries") is not None and actual > 0:
        rec = erp_of(kb, review["recommended_gantries"], share)
        if rec is None:
            reasons.append("FC-R-INSUFFICIENT-DATA")
            return finish("ESCALATE_HUMAN")
        diff = _r2(actual - rec)
        steps.append(("FC-R08", f"ERP(actual) {actual:.2f} minus ERP(recommended) {rec:.2f} = {diff:.2f}"))
        if diff > 0:
            metered = kb.resolve("TX-SERVICE", trip.get("service_type")) == "RYDETAXI" or "metered" in str(trip.get("fare_type", "")).lower()
            if metered:                                                                              # FC-F01: RydeTAXI is METERED; D32: in line with FC-R00
                attach.update(erp_actual=actual, erp_recommended=rec, difference=diff, information_only=True)
                if over:
                    attach["fc_r07_overstatement"] = over
                reasons[:] = ["GEN-R-POLICY-GAP"]
                steps.append(("GEN-R07", "FC-R08 does not rule on a metered fare (D32)"))
                return finish("ESCALATE_HUMAN")
            decisive.append(("FC-F03", "reading the justification the other way would change the amount"))
            if not review.get("justification"):
                detour = diff
                reasons.append("FC-R-TOLL-FROM-DETOUR")
            else:
                steps.append(("FC-F03", f"deviation justified: {review['justification']}"))
    refund = _r2(min(over + detour, charged))
    if refund > 0:
        return finish("TOLL_REFUND", refund)
    reasons.append("FC-R-TOLL-VALID")
    return finish("UPHOLD", 0.0)


def fc_r01(kb: KB, case: dict) -> dict:
    """FC-R01 on a route ticket: fixed fare and charged = quoted means no fare refund, and the ERP the longer route caused is
    never closed here: it goes to its own FC-TOLL claim (run above) whenever the actual path passed gantries that the
    recommended route avoids."""
    trip, fare = case.get("trip_data", {}), case.get("fare_breakdown", {})
    mode = "METERED" if "metered" in str(trip.get("fare_type", "")).lower() else "FIXED_AT_BOOKING"
    fixed_same = mode == "FIXED_AT_BOOKING" and trip.get("quoted_fare") is not None and abs(float(trip["quoted_fare"]) - float(fare.get("base_fare", -1))) < 0.005
    actual = [g["gantry"] for g in (case.get("erp_charges") or {}).get("gantry_passes", []) if g.get("active", True)]
    rec = [g["gantry"] for g in (case.get("route_review") or {}).get("recommended_gantries") or []]
    extra = [g for g in actual if g not in rec] if (case.get("route_review") or {}).get("recommended_gantries") is not None else []
    return {"applies": fixed_same, "fare_refund": 0.0 if fixed_same else None, "reason": "FC-R-FIXED-FARE" if fixed_same else None,
            "toll_claim": run(kb, case) if (fixed_same and extra) else None, "extra_gantries": extra}

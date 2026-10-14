"""Reference evaluation of PB-FC-TOLL (ERP disputes) on an organizer-format case such as round 1 case E11 and its variants.

Purpose: make the ERP rules testable the way engine_noshow.py does for the no-show fee: FC-R06 (the rider's share) first, then
FC-F04 (expected ERP), FC-R07 (ERP overstated), FC-F03 and FC-R08 (ERP caused by an unjustified detour), and FC-R01 (which sends
detour ERP to its own FC-TOLL claim). It is a verification tool for the knowledge base, not the product engine:
- there is no LLM: the READ part of FC-F03 (is the detour justified?) is an input of the case (route_review.justification),
  and the run-agreement and rules-engine confidence terms of AUTH-05 are not computed, so tier AUTO here means that no
  approval trigger fired, before the confidence test;
- only the rules named above are applied (no MAT, DQ or META-02 date check); FC-R12 applies to missing or unusable gantry
  data, a missing recommended route, and a changed itinerary whose recommended route is not shown to follow it.
Case fields read: trip_data.service_type, trip_data.is_carpool, trip_data.fare_type, trip_data.quoted_fare,
fare_breakdown.erp_toll (the ERP line the rider was charged) and base_fare, erp_charges.gantry_passes (timestamp, gantry,
active, rate_sgd), route_review.recommended_gantries (the gantries of the recommended route), route_review.justification and
route_review.final_itinerary (true when that route follows the final itinerary, FC-F02), and the records of an itinerary that
changed during the trip (itinerary_change: trip_data.destination_edit_accepted, the app events destination_edit_accepted,
stop_added and destination_edit_requested, system messages, a destination-change fee line).
"""
from __future__ import annotations

import math
import re
from collections import Counter

from kbload import KB

PROFILE = "ryde_2026"       # ERP parameters are shared; the profile only supplies AUTO_LIMIT_SGD through the shared fallback


def _r2(x: float) -> float:
    return round(x + 1e-9, 2)


def _flat(x) -> str:
    return re.sub(r"[^a-z0-9]", "", str(x).lower().replace("+", "plus"))


def service_code(kb: KB, trip: dict) -> str | None:
    """The TX-SERVICE code of the trip, or None when the service type is not recorded or not recognized."""
    raw = trip.get("service_type")
    if raw is None or not str(raw).strip():
        return None
    code = kb.resolve("TX-SERVICE", raw)
    if code is None:                                    # "Ryde Send", "ryde_send", the label "Carpooling" or "Ryde+"
        flat = _flat(raw)
        code = next((c for c, v in kb.vocab["TX-SERVICE"].items() if flat in (_flat(c), _flat(v.get("label", "")))), None)
    return None if code in (None, "UNKNOWN") else code


def _num(x) -> float | None:
    """A finite number, or None for a missing, empty, non-numeric, NaN or infinite value (the caller sends None to FC-R12)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _flag(x, default=None):
    """A boolean field as an extractor may write it: True/'true'/'yes'/1 and False/'false'/'no'/0; None or '' gives the default;
    anything else is unparseable and gives None (insufficient data)."""
    if x is None or (isinstance(x, str) and not x.strip()):
        return default
    t = str(x).strip().lower()
    if t in ("true", "yes", "y", "1"):
        return True
    if t in ("false", "no", "n", "0"):
        return False
    return None


_CHANGE_ON = r"(?<![a-z])(destination|drop[_\- ]?off|stops?|itinerary)(?![a-z])"          # what changed
_CHANGE_ACT = r"\b(edit\w*|chang\w*|add(ed|s|ing)?|new|updat\w*|modif\w*|request\w*|set)\b"          # that it was changed or asked for
_ACCEPTED = r"accept|approv|confirm|changed|updated|recalculat"
_DECLINED = r"declin|reject|refus|withdr|not accepted|not approved|cancel+ed (the |this |your )?(request|edit|change)"


def _amount(v) -> float | None:
    """A fee line as a number: 3, '3.00', '$3.00' or 'S$3.00'."""
    return _num(re.sub(r"^[^\d\-.]*", "", str(v))) if v is not None else None


def itinerary_change(case: dict) -> bool | None:
    """FC-F01, FC-F02: did the itinerary change during the trip? Each record that is about a change of destination, drop-off
    or stop (the trip flag, an app event's type or details, a system message, a destination-change fee line) is read as
    accepted, declined or open. True when a record shows the change accepted and the flag does not deny it; None when a
    record points to a change that no record shows accepted or declined (an unparseable flag, a request alone, wording
    this reader cannot settle), or the records disagree: the fare may have been recalculated, so the caller sends it to
    FC-R12; False otherwise (no such record, or every request declined: 'If the driver rejects, the previous trip details
    remain'). Negation is read only in the sentence that carries the acceptance (A4 check round 2)."""
    trip, fare = case.get("trip_data") or {}, case.get("fare_breakdown") or {}
    flag = _flag(trip.get("destination_edit_accepted"), "absent")
    accepted, opened, declined = 0, 0, 0

    def read(text):
        nonlocal accepted, opened, declined
        for sent in re.split(r"(?<=[.;!?])\s+", text):
            if re.search(_DECLINED, sent, re.I):
                declined += 1
                return
            if re.search(_ACCEPTED, sent, re.I) and not re.search(r"\b(not|no longer)\b", sent, re.I):
                accepted += 1
                return
        opened += 1
    for ev in case.get("app_events") or []:
        et = re.sub(r"[\s\-]+", "_", str(ev.get("event_type", "")).strip().lower())
        txt = et.replace("_", " ") + ". " + str(ev.get("details") or "")
        if re.search(_CHANGE_ON, et.replace("_", " ")) and re.search(_CHANGE_ACT, txt, re.I):
            read(txt)
    for c in case.get("chat_logs") or []:
        if str(c.get("type", "")).strip().lower() == "system":
            txt = str(c.get("content", ""))
            if re.search(_CHANGE_ON, txt, re.I) and re.search(_CHANGE_ACT, txt, re.I):
                read(txt)
    for k, v in fare.items():
        key = re.sub(r"[\s\-]+", "_", str(k).lower())
        if (re.search(r"(^|_)(destination|dropoff|drop_off|stop|edit|add_stop|change)(_|$)", key)
                and not re.search(r"credit|discount|promo|refund|voucher|card|bus", key) and (_amount(v) or 0) > 0):
            accepted += 1                       # the add/edit destination fee applies only if the driver accepts (FC-F01)
    if flag is True:
        accepted += 1
    if accepted:
        return True if flag in (True, "absent") else None   # an explicit 'false' flag against an acceptance: the records disagree
    if flag is None or opened > declined:
        return None
    return False


def _active(g: dict) -> bool:
    return _flag(g.get("active"), True) is not False        # an unparseable value counts as active (the safe direction: more ERP expected)


def is_metered(kb: KB, trip: dict) -> bool:
    """FC-F01: RydeTAXI is METERED; a fare_type that says 'metered' (not 'non-metered', 'unmetered' or 'not metered') too."""
    t = str(trip.get("fare_type", "")).lower()
    return service_code(kb, trip) == "RYDETAXI" or (not re.search(r"\b(?:not|non|un)[- ]?metered", t) and bool(re.search(r"\bmetered\b", t)))


def rider_share(kb: KB, case: dict) -> dict:
    """FC-R06: {"share", "basis", "gap", "assumed"}. gap is None, "UNRECORDED" (FC-R12) or "NO_RULE" (GEN-R07: no share).
    A trip is a carpool trip only when the record says so (service type CARPOOL, or is_carpool true); the carpool half applies to
    CARPOOL and to the six services Ryde names, and any other service flagged as carpool has no rule. For RydeFLASH, which Ryde
    offers to carpool drivers, an is_carpool that is not recorded is assumed false and 'assumed' says so (records missing)."""
    trip = case.get("trip_data", {})
    code = service_code(kb, trip)
    table = kb.tables["ERP_RIDER_SHARE"]["value"]
    flag = _flag(trip.get("is_carpool"))
    carpool = code == "CARPOOL" or flag is True
    if code is None:
        return {"share": None, "gap": "UNRECORDED", "basis": "service type not recorded (FC-R12)", "assumed": None}
    if trip.get("is_carpool") is not None and str(trip.get("is_carpool")).strip() != "" and flag is None:
        return {"share": None, "gap": "UNRECORDED", "basis": "is_carpool is not a yes or no (FC-R12)", "assumed": None}
    if code == "RYDESEND" and carpool:
        return {"share": None, "gap": "NO_RULE", "basis": "RydeSEND and carpool at once: no order in Ryde's articles", "assumed": None}
    if carpool:
        if code != "CARPOOL" and code not in table:
            return {"share": None, "gap": "NO_RULE", "basis": f"{code} flagged as carpool: Ryde sets no share for it", "assumed": None}
        return {"share": float(table["CARPOOL"]), "gap": None, "basis": "FC-R06 carpool", "assumed": None}
    if code in table:
        assumed = "RydeFLASH is offered to carpool drivers and is_carpool is not recorded: assumed not a carpool trip" if (code == "RYDEFLASH" and flag is None) else None
        return {"share": float(table[code]), "gap": None, "basis": f"FC-R06 {code}", "assumed": assumed}
    return {"share": None, "gap": "NO_RULE", "basis": f"{code}: Ryde's 2026 driver article sets no share", "assumed": None}


def gantry_rate(kb: KB, g: dict) -> float | None:
    """The rate in the trip's own gantry log, else the LTA table row for that gantry and time of day (they can differ: open item D35)."""
    if g.get("rate_sgd") is not None and str(g.get("rate_sgd")).strip() != "":
        return _num(g["rate_sgd"])
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
        if not _active(g):
            continue
        r = gantry_rate(kb, g)
        if r is None:
            return None
        total += r
    return _r2(share * total)


def run(kb: KB, case: dict, profile: str = PROFILE) -> dict:
    """profile: ryde_2026 (the default and the regression profile) or organizer_v2_1, where TOLLS_TREATMENT = PASS_THROUGH means FC-R08 refunds nothing (D47)."""
    trip, fare = case.get("trip_data", {}), case.get("fare_breakdown", {})
    pass_through = kb.pval("TOLLS_TREATMENT", profile) == "PASS_THROUGH"
    steps, flags, reasons, fraud, triggers, decisive, attach = [], [], [], [], [], [], {}
    out = {"steps": steps, "flags": flags, "reasons": reasons, "fraud": fraud, "attach": attach, "amount": None}

    def finish(outcome, amount=None):
        if decisive:
            flags.append("GENERIC_ASSUMPTION_USED")           # META-05: a rule rated C or D (FC-F03) or a D parameter is decisive
        limit = kb.pval("AUTO_LIMIT_SGD", profile)
        if outcome != "ESCALATE_HUMAN" and amount is not None and amount > limit:
            triggers.append(f"amount S${amount:.2f} above AUTO_LIMIT_SGD S${limit:.2f}")
        tier = "HUMAN" if outcome == "ESCALATE_HUMAN" else ("APPROVE" if triggers or decisive else "AUTO")
        out.update(outcome=outcome, amount=amount, tier=tier, triggers=triggers, decisive=decisive)
        return out

    sh = rider_share(kb, case)                                                                        # PB-FC-TOLL 1: FC-R06
    share = sh["share"]
    steps.append(("FC-R06", f"share {share}: {sh['basis']}"))
    if sh["assumed"]:
        flags.append("RECORDS_MISSING")
        triggers.append(sh["assumed"])
    if sh["gap"]:
        if sh["gap"] == "UNRECORDED":
            reasons.append("FC-R-INSUFFICIENT-DATA")
            if "RECORDS_MISSING" not in flags:
                flags.append("RECORDS_MISSING")
        else:
            reasons.append("GEN-R-POLICY-GAP")
            steps.append(("GEN-R07", sh["basis"]))
        return finish("ESCALATE_HUMAN")
    gantries = (case.get("erp_charges") or {}).get("gantry_passes")
    charged = _num(fare.get("erp_toll"))
    actual = erp_of(kb, gantries, share) if gantries is not None else None                           # PB-FC-TOLL 2: FC-F04
    if actual is None or charged is None or charged < 0:
        reasons.append("FC-R-INSUFFICIENT-DATA")
        steps.append(("FC-R12", "no gantry log, a gantry without a rate, or no usable ERP line charged"))
        return finish("ESCALATE_HUMAN")
    charged = _r2(charged)
    steps.append(("FC-F04", f"expected ERP {actual:.2f} for the rider (charged {charged:.2f})"))
    out["expected"] = actual
    tol_lo, tol_hi = kb.param("TOLL_TOLERANCE_SGD", profile)["plausible_range"]
    tol = kb.pval("TOLL_TOLERANCE_SGD", profile)
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
    review = case.get("route_review")
    if review is not None and review.get("recommended_gantries") is None:   # a detour question was raised, but the recommended route is unknown
        reasons[:] = ["FC-R-INSUFFICIENT-DATA"]
        steps.append(("FC-R12", "route_review without the gantries of the recommended route"))
        if over:
            attach["fc_r07_overstatement"] = over
        return finish("ESCALATE_HUMAN")
    changed = itinerary_change(case)                                                                  # FC-F02, FC-R12 (A4, FX7)
    if (review is not None and changed is not False and _flag(review.get("final_itinerary"), False) is not True
            and actual > 0 and charged > 0):                   # only when the recommended route can change the amount (FC-R08)
        reasons[:] = ["FC-R-INSUFFICIENT-DATA"]
        steps.append(("FC-R12", "the itinerary " + ("changed" if changed else "may have changed") + " during the trip and the recommended "
                      "route on record is not shown to follow the final itinerary"))
        if over:
            attach["fc_r07_overstatement"] = over
        return finish("ESCALATE_HUMAN")
    review = review or {}
    if review.get("recommended_gantries") is not None and actual > 0:
        rec = erp_of(kb, review["recommended_gantries"], share)
        if rec is None:
            reasons[:] = ["FC-R-INSUFFICIENT-DATA"]
            if over:
                attach["fc_r07_overstatement"] = over
            return finish("ESCALATE_HUMAN")
        diff = _r2(actual - rec)                           # the extra ERP the detour caused, at the rider's share
        steps.append(("FC-R08", f"ERP(actual) {actual:.2f} minus ERP(recommended) {rec:.2f} = {diff:.2f}"))
        if diff > 0:
            if is_metered(kb, trip):                                                                 # D32: in line with FC-R00
                attach.update(erp_actual=actual, erp_recommended=rec, difference=diff, information_only=True)
                if over:
                    attach["fc_r07_overstatement"] = over
                reasons[:] = ["GEN-R-POLICY-GAP"]
                steps.append(("GEN-R07", "FC-R08 does not rule on a metered fare (D32)"))
                return finish("ESCALATE_HUMAN")
            potential = _r2(max(0.0, min(actual, charged) - rec))     # what the rider paid above ERP(recommended), up to diff
            if potential > 0 and pass_through:                                                       # organizer_v2_1: tolls pass through at cost (D47)
                steps.append(("FC-R08", "the tolls of the longer route pass through at cost under this profile: nothing is refunded for the detour (D47)"))
            elif potential > 0:
                decisive.append(("FC-F03", "reading the justification the other way would change the amount"))
                if not review.get("justification"):
                    detour = potential
                    reasons.append("FC-R-TOLL-FROM-DETOUR")
                else:
                    steps.append(("FC-F03", f"deviation justified: {review['justification']}"))
    refund = _r2(over + detour)
    if refund > 0:
        return finish("TOLL_REFUND", refund)
    reasons.append("FC-R-TOLL-VALID")
    return finish("UPHOLD", 0.0)


def fc_r01(kb: KB, case: dict, profile: str = PROFILE) -> dict:
    """FC-R01 on a route ticket: fixed fare and charged = quoted means no fare refund, and the ERP the longer route caused is
    never closed here: it goes to its own FC-TOLL claim (run above) whenever the actual path passed gantries that the
    recommended route avoids, or passed them more often (FairRyde's reading of the ERP difference, open item D35). Without the
    gantries of the recommended route the claim cannot be opened and FC-R12 applies."""
    trip, fare = case.get("trip_data", {}), case.get("fare_breakdown", {})
    change = itinerary_change(case)                                                                   # FC-F01: RECALCULATED
    if change is None and not is_metered(kb, trip):     # the fare may have been recalculated: FC-R01 cannot be applied (FC-R12)
        return {"applies": None, "fare_refund": None, "reason": None, "toll_claim": None, "extra_gantries": [], "escalate": "FC-R12"}
    recalculated = change is True
    quoted, base = _num(trip.get("quoted_fare")), _num(fare.get("base_fare"))
    fixed_same = (not is_metered(kb, trip) and not recalculated and quoted is not None and base is not None and abs(quoted - base) < 0.005)
    passes = (case.get("erp_charges") or {}).get("gantry_passes") or []
    actual = Counter(g.get("gantry") for g in passes if _active(g))
    rg = (case.get("route_review") or {}).get("recommended_gantries")
    extra = sorted((actual - Counter(g.get("gantry") for g in rg if _active(g))).elements(), key=str) if rg is not None else []
    needs_r12 = fixed_same and rg is None and bool(actual)
    claim = run(kb, case, profile) if (fixed_same and extra and kb.pval("TOLLS_TREATMENT", profile) != "PASS_THROUGH") else None
    return {"applies": fixed_same, "fare_refund": 0.0 if fixed_same else None, "reason": "FC-R-FIXED-FARE" if fixed_same else None,
            "toll_claim": claim, "extra_gantries": extra, "escalate": "FC-R12" if needs_r12 else None}

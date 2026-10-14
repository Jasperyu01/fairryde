"""Policy v2.1 helpers shared by the engines of profile organizer_v2_1: the Section 6 ruling path, the AUTH-05 confidence, the precedent search
(Section 7) and the evidence index of the route and surge cases.

Mapping of the policy's ruling paths to FairRyde's three autonomy tiers (rule AUTH-07, decision D48; FairRyde's reading of the words):
  "AI agent ruling is final"                                  -> AUTO    (nobody approves; both parties can still ask for a review)
  "escalate to human review" with a ruling FairRyde proposes   -> APPROVE (a person confirms or changes the recommended remedy)
  "always human review ... AI agent prepares case file only"   -> HUMAN   (no outcome, amount or measure is proposed)
"""
from __future__ import annotations

from kbload import KB, ORGANIZER_PROFILE

TIER_ORDER = {"AUTO": 0, "APPROVE": 1, "HUMAN": 2}


def fraud_flag_count(case: dict) -> int:
    """Section 6.3: 'If any party has a fraud flag >= 1': the larger count of the two profiles."""
    out = 0
    for key in ("rider_profile", "driver_profile"):
        try:
            out = max(out, int((case.get(key) or {}).get("fraud_flags") or 0))
        except (TypeError, ValueError):
            out = max(out, 1)               # an unreadable flag count is treated as a flag (the safe direction)
    return out


def composite_confidence(kb: KB, profile: str, margin_term: float, required: dict, soft_flags: list, d29_penalty: float = 0.0) -> dict:
    """AUTH-05: C = wA x A + wM x M + wE x E + wR x R. A and R are 1.0 because no LLM runs in this check. d29_penalty is the
    organizer_v2_1 form of decision D29 (a confidence penalty instead of an approval trigger, D52)."""
    w = kb.pval("CONFIDENCE_WEIGHTS", profile)
    pen = kb.pval("SOFT_FLAG_PENALTY", profile)
    E_ = max(0.0, sum(required.values()) / len(required) - pen * len(soft_flags))
    c_raw = w["A_run_agreement"] * 1.0 + w["M_threshold_margin"] * margin_term + w["E_evidence_completeness"] * E_ + w["R_rules_engine_agreement"] * 1.0
    return {"A": 1.0, "M": round(margin_term, 3), "E": round(E_, 3), "R": 1.0, "C": round(c_raw, 3), "d29_penalty": d29_penalty,
            "C_effective": round(c_raw - d29_penalty, 3), "assumed": ["A = 1.0 (no LLM runs in this check)", "R = 1.0 (no LLM Judge in this check)"],
            "soft_flags": list(soft_flags), "evidence_present": dict(required)}


def ruling_path(kb: KB, profile: str, *, category: str, value: float, confidence: float, fraud_flags: int,
                deviation_km: float | None = None) -> dict:
    """Sections 6.1 to 6.3 for one ruling (rule AUTH-07). value is the amount in dispute in S$; confidence is C after the D29 penalty.
    Returns the tier the policy asks for and the reason of each constraint that applies, the deciding one first. Safety (Section 5.2)
    and a case-file-only handling are decided by the caller; this function never lowers a tier the caller has set."""
    p = lambda name: kb.pval(name, profile)
    below, above = p("RULING_FINAL_BELOW_SGD"), p("HUMAN_REVIEW_ABOVE_SGD")
    conf_min, conf_fraud = p("CONFIDENCE_MIN"), p("CONFIDENCE_MIN_FRAUD_FLAG")
    band = "FINAL" if value < below else ("REVIEW" if value > above else "CONFIDENCE")
    needed, why_needed = None, None
    if band == "CONFIDENCE":
        needed, why_needed = conf_min, f"Section 6.1: a dispute of S${below:.0f} to S${above:.0f} needs {conf_min:.0%} confidence"
    if category == "route_deviation":              # Section 6.2: 80% for every route deviation, whatever its value
        if needed is None or conf_min > needed:
            needed, why_needed = conf_min, f"Section 6.2: a route deviation ruling needs {conf_min:.0%} confidence"
    if fraud_flags >= 1:                           # Section 6.3: raised to 95% regardless of dispute value
        needed, why_needed = conf_fraud, f"Section 6.3: a party has a fraud flag ({fraud_flags}), so the confidence threshold is raised to {conf_fraud:.0%} regardless of dispute value"
    reasons, tier = [], "AUTO"

    def raise_to(t, why):
        nonlocal tier
        reasons.append(why)
        if TIER_ORDER[t] > TIER_ORDER[tier]:
            tier = t
    if band == "REVIEW":
        raise_to("HUMAN", f"Section 6.1: a dispute above S${above:.0f} (S${value:.2f}) is always human review; the AI agent prepares the case file only")
    if category == "route_deviation" and deviation_km is not None and deviation_km > p("ROUTE_AI_MAX_KM"):
        raise_to("APPROVE", f"Section 6.2: the deviation of {deviation_km:.{2 if round(deviation_km, 1) <= p('ROUTE_AI_MAX_KM') else 1}f} km is above the {p('ROUTE_AI_MAX_KM'):.1f} km an AI ruling may decide, so the ruling goes to human review with the remedy FairRyde recommends")
    if needed is not None and confidence < needed - 1e-9:
        raise_to("APPROVE", f"{why_needed}; this ruling's confidence is {confidence:.2f}, so it goes to human review with the remedy FairRyde recommends")
    if not reasons:
        reasons.append(f"Section 6.1: the dispute is under S${below:.0f} (S${value:.2f}), so the AI ruling is final" if band == "FINAL" and needed is None
                       else f"{why_needed}; this ruling's confidence is {confidence:.2f}, which meets it")
    return {"tier": tier, "band": band, "threshold": needed, "reasons": reasons, "value": value, "confidence": confidence, "fraud_flags": fraud_flags}


def evidence_index(case: dict) -> dict:
    """ID-addressed evidence of a route or surge case (ontology ENT-EVIDENCE; E-RTE, E-TRF and E-SRG are new in KB v0.3)."""
    E = {"E-TKT-01": {"type": "statement", "tier": "D", "summary": "Ticket; the description is the claimant's own statement (tier D).", "untrusted_text": True},
         "E-PRF-R": {"type": "profile_stat", "tier": "A", "summary": "Rider profile (history, rating, flags). Never decisive (GEN-R03)."},
         "E-PRF-D": {"type": "profile_stat", "tier": "A", "summary": "Driver profile (history, rating, flags). Never decisive (GEN-R03)."},
         "E-TRP-01": {"type": "trip_record", "tier": "A", "summary": "Trip record (times, distances, fares)."}}
    if case.get("fare_breakdown"):
        E["E-PAY-01"] = {"type": "charge_record", "tier": "A", "summary": "Fare breakdown (quote, actual fare, excess and surge lines)."}
    if case.get("optimal_route"):
        E["E-RTE-01"] = {"type": "reference_lookup", "tier": "A", "summary": "System-recommended route (waypoints, distance, duration)."}
    if case.get("surge_pricing_log"):
        E["E-SRG-01"] = {"type": "app_event", "tier": "A", "summary": "Platform surge record (multipliers, activation time, rider notification)."}
    for i, g in enumerate(case.get("gps_telemetry") or [], 1):
        E[f"E-GPS-{i:02d}"] = {"type": "gps_ping", "tier": "B", "ts": g["timestamp"], "summary": f"{g['timestamp'][11:19]} speed {g.get('speed_kmh')} km/h"}
    for i, c in enumerate(case.get("chat_logs") or [], 1):
        E[f"E-CHT-{i:02d}"] = {"type": {"message": "chat_message", "call": "call_log", "system": "app_event"}.get(c["type"], "other"),
                               "tier": {"message": "C", "call": "A", "system": "A"}.get(c["type"], "D"), "ts": c["timestamp"],
                               "summary": f"{c['timestamp'][11:19]} {c['sender']} {c['type']}", "untrusted_text": c["type"] == "message"}
    for i, t in enumerate(case.get("traffic_conditions") or [], 1):
        E[f"E-TRF-{i:02d}"] = {"type": "reference_lookup", "tier": "A", "ts": t.get("timestamp"), "summary": f"{t.get('incident_id')} {t.get('road')} {t.get('incident_type')} ({t.get('severity')})"}
    return E


def match_precedents(kb: KB, taxonomy_code: str, factors: dict) -> list[dict]:
    """Section 7: search the precedents by dispute type and key facts. A precedent is ALIGNED when every key factor of the precedent has the
    same value in this case (a count is compared as none or some), else DISTINGUISHED, with the factors that differ."""
    def norm(v):
        return (v > 0) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
    out = []
    for pid, pr in kb.precedents.items():
        if pr["taxonomy_code"] != taxonomy_code:
            continue
        same, differs = [], []
        for k in pr["key_factors"]:
            (same if k in factors and norm(factors[k]) == norm(pr["factor_vector"][k]) else differs).append(k)
        out.append({"id": pid, "section": pr["section"], "case_id": pr["case_id"], "aligned": not differs, "same": same, "differs": differs,
                    "outcome": pr["outcome"], "refund_amount_sgd": pr["refund_amount_sgd"], "confidence": pr["confidence"]})
    return out

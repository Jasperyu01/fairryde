"""One entry point for the reference engines: pick the engine from the claim type and the profile, and score an organizer sample against its
expected ruling.

    run_case(kb, case)            # profile by META-01: organizer_v2_1 for an organizer case (a DISP-nnn id), else as before
    score(kb, "DISP-001", result) # the organizer's expected outcome and amount, and the tier the brief asks of policy v2.1 Section 6

No-show (CW-NOSHOW) runs on engine_noshow.py under any profile; a route deviation (FC-ROUTE) and a surge dispute (FC-SURGE) run on
engine_route.py and engine_surge.py under organizer_v2_1 only (the Ryde profile's route rules are applied by the rule cards, with
engine_toll.py for ERP); an ERP case (dispute_type erp_toll) runs on engine_toll.py under ryde_2026.
"""
from __future__ import annotations

import case_adapter
import engine_noshow
import engine_route
import engine_surge
import engine_toll
import explain
from kbload import KB, ORGANIZER_PROFILE, default_profile


def claim_type(kb: KB, case: dict) -> str | None:
    code = kb.resolve("TX-CASE", case["dispute_ticket"]["dispute_type"])
    if code == "FC-SURGE" and not engine_surge.has_surge_evidence(case):
        return "FC-FAREMISMATCH"
    return code


def run_case(kb: KB, case: dict, profile: str | None = None) -> dict:
    canon, _ref = case_adapter.prepare(case)
    profile = profile or default_profile(canon)
    if canon["dispute_ticket"]["dispute_type"] == "erp_toll":
        r = engine_toll.run(kb, canon)
        return {"engine": "engine_toll", "profile": "ryde_2026", "result": r}
    code = claim_type(kb, canon)
    if code == "CW-NOSHOW":
        return {"engine": "engine_noshow", "profile": profile, "result": engine_noshow.run(kb, canon, profile)}
    if code == "FC-ROUTE" and profile == ORGANIZER_PROFILE:
        return {"engine": "engine_route", "profile": profile, "result": engine_route.run(kb, canon, profile)}
    if code in ("FC-SURGE", "FC-FAREMISMATCH") and profile == ORGANIZER_PROFILE:
        return {"engine": "engine_surge", "profile": profile, "result": engine_surge.run(kb, canon, profile)}
    raise NotImplementedError(f"no reference engine for {code} under {profile}")


def score(kb: KB, case_id: str, result: dict) -> dict:
    """Compare a result of an organizer sample with the expected ruling of kb.expected (outcome, amount, tier, reasons)."""
    exp = kb.expected[case_id]
    t, tier = result["trace"], result["tier"]
    amount = (t.remedy or {}).get("amount_sgd") if t.outcome in ("PARTIAL_REFUND", "FULL_REFUND", "WAIVE_FEE", "TOLL_REFUND") else None
    problems = []
    if t.outcome != exp["expected_outcome"]:
        problems.append(f"outcome {t.outcome}, expected {exp['expected_outcome']}")
    want = exp.get("expected_amount_sgd")
    if want is not None and (amount is None or abs(amount - want) > 0.005):
        problems.append(f"amount {amount}, expected {want}")
    if want is None and t.outcome == "UPHOLD" and amount not in (None, 0.0):
        problems.append(f"amount {amount}, expected none")
    if tier["tier"] != exp["expected_tier"]:
        problems.append(f"tier {tier['tier']}, expected {exp['expected_tier']}")
    for r in exp.get("expected_reasons", []):
        if r not in t.reasons:
            problems.append(f"reason {r} missing from {t.reasons}")
    return {"case": case_id, "ok": not problems, "problems": problems, "outcome": t.outcome, "amount": amount, "tier": tier["tier"], "reasons": t.reasons}


def explanation(kb: KB, result: dict) -> dict:
    return explain.policy_v21(kb, result)

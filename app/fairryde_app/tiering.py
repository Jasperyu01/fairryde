"""Stage 7: the approval tier (AUTH rules, profile organizer_v2_1 for organizer cases).

The reference engine already applies AUTH-01 to AUTH-06 and, under organizer_v2_1, AUTH-07 (policy v2.1 Section 6) with the confidence it can
compute offline (A and R are 1.0 there). With an LLM Judge in the loop the confidence has a second source, so the app recomputes Section 6 with
the lower of the two (the Judge never raises the engine's confidence), and the tier is the strictest of:

  1. the engine's tier (its triggers: fraud signal, decisive readings, margin, D29 and so on),
  2. policy v2.1 Section 6 on the final confidence (organizer cases) or the profile's TAU (other profiles),
  3. the tier the Judge proposed (a Judge may be more cautious than the rules, never less).

Tiers: AUTO (final, both parties can ask for a review), APPROVE (a person confirms or changes the recommended remedy), HUMAN (a person decides,
the agents prepare the case file only). The mapping of the policy's words to tiers is decision D48 in kb/open_items.yaml.
"""
from __future__ import annotations

from .kbaccess import ORGANIZER_PROFILE, P21

ORDER = {"AUTO": 0, "APPROVE": 1, "HUMAN": 2}
SECTION6_CATEGORY = {"CW-NOSHOW": "no_show", "FC-ROUTE": "route_deviation", "FC-SURGE": "fare_dispute", "FC-FAREMISMATCH": "fare_dispute"}


def stricter(*tiers) -> str:
    return max((t for t in tiers if t in ORDER), key=lambda t: ORDER[t], default="HUMAN")


def final_confidence(judge_conf, engine_out: dict) -> dict:
    """The lower of the Judge's confidence and the engine's C (after the D29 penalty under organizer_v2_1)."""
    c = engine_out.get("confidence") or {}
    eng = c.get("C_effective", c.get("C"))
    vals = [v for v in (judge_conf, eng) if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return {"judge": judge_conf, "engine": eng, "final": round(min(vals), 3) if vals else None,
            "rule": "the lower of the Judge's confidence and the engine's C (the Judge never raises it)"}


def section6(kb, engine_out: dict, confidence: float | None) -> dict | None:
    """Policy v2.1 Sections 6.1 to 6.3 for this ruling (rule AUTH-07); None outside organizer_v2_1."""
    if engine_out["profile"] != ORGANIZER_PROFILE or confidence is None:
        return None
    category = SECTION6_CATEGORY.get(engine_out["claim_type"] or "")
    if category is None or engine_out.get("amount_at_stake") is None:
        return None
    return P21.ruling_path(kb, ORGANIZER_PROFILE, category=category, value=engine_out["amount_at_stake"], confidence=confidence,
                           fraud_flags=engine_out["fraud_flags"], deviation_km=engine_out.get("deviation_km"))


def tier_for_ruling(kb, engine_out: dict, judge_conf, judge_tier: str | None) -> dict:
    """The tier of a ruling both the engine and the Judge stand behind."""
    conf = final_confidence(judge_conf, engine_out)
    reasons: list[str] = []
    tiers = [engine_out["engine_tier"]]
    sec6 = section6(kb, engine_out, conf["final"])
    below = False
    if sec6:
        tiers.append(sec6["tier"])
        if sec6["tier"] != "AUTO":
            reasons += sec6["reasons"]
        below = sec6["threshold"] is not None and conf["final"] is not None and conf["final"] < sec6["threshold"] - 1e-9
    elif engine_out["profile"] != ORGANIZER_PROFILE and conf["final"] is not None:
        from .kbaccess import get_kb
        tau = get_kb().pval("TAU", engine_out["profile"])
        if tau is not None and conf["final"] < tau:
            tiers.append("APPROVE")
            below = True
            reasons.append(f"confidence {conf['final']:.2f} is below TAU {tau} for profile {engine_out['profile']} (AUTH-01): a person confirms the ruling")
    if judge_tier in ORDER:
        tiers.append(judge_tier)
    tier = stricter(*tiers)
    if engine_out["engine_tier"] != "AUTO":
        reasons = [t for t in engine_out["triggers"] if not t.lower().startswith("fraud signal")][:3] + reasons
    return {"tier": tier, "engine_tier": engine_out["engine_tier"], "judge_tier": judge_tier, "section6": sec6, "confidence": conf,
            "below_threshold": below, "reasons": list(dict.fromkeys(reasons))}

"""Executable form of escalation gate G3 (AUTH-04), the one gate the offline engines cannot detect by themselves.

G3 fires when the history-aware Judge pass or the fraud check disagrees with the history-blind pass. Detecting the
disagreement needs those runtime passes; what to do about it is fixed by rule card AUTH-04 and implemented here, so that
it can be tested: the history-blind ruling stays as the provisional ruling at tier APPROVE (history never decides an
outcome, GEN-R03 and FRD-02), the history-aware result is only shown to the reviewer, and a history-blind pass that has no
ruling itself (ESCALATE_HUMAN) stays ESCALATE_HUMAN at tier HUMAN (AUTH-06). The tier of each gate is read from the
gate_tiers field of AUTH-04, never written again here.
"""
from __future__ import annotations

from kbload import KB

_ORDER = {"AUTO": 0, "APPROVE": 1, "HUMAN": 2}


def gate_tier(kb: KB, gate: str) -> str:
    return kb.rules["AUTH-04"]["gate_tiers"][gate]


def resolve_g3(kb: KB, blind: dict, aware: dict | None = None, fraud_check_disagrees: bool = False) -> dict:
    """blind and aware are rulings {"outcome", "amount", "tier"} (aware needs only outcome and amount). Returns the ruling
    that goes to the reviewer: the history-blind outcome and amount, the tier, and what the reviewer is shown."""
    differs = bool(aware) and (aware.get("outcome") != blind.get("outcome") or aware.get("amount") != blind.get("amount"))
    fired = differs or fraud_check_disagrees
    tier = blind["tier"]
    if tier not in _ORDER and not str(tier).startswith("n/a"):       # "n/a (reclassified to ...)" is what decide_tier writes for a case that is not ruled
        raise ValueError(f"unknown tier {tier!r}: expected AUTO, APPROVE or HUMAN")
    if fired:
        if blind["outcome"] == "ESCALATE_HUMAN" or blind["outcome"] is None:
            tier = "HUMAN"
        else:                                           # a tier the engine did not set (for example a reclassified case) counts as the lowest
            tier = max(tier, gate_tier(kb, "G3"), key=lambda t: _ORDER.get(t, -1))
    return {"gate": "G3" if fired else None, "outcome": blind["outcome"], "amount": blind.get("amount"), "tier": tier,
            "shown_to_reviewer": {"history_aware": aware, "fraud_check_disagrees": fraud_check_disagrees} if fired else None}

"""Stage 7 (continued): turn the Judge's answer, the verifier's report and the engine result into the ruling the app shows and stores.

Four outcomes of the checking, in the order the pipeline meets them:
  case file   safety (policy v2.1 Section 5.2) or no written rule in code (GEN-R07): ESCALATE_HUMAN, no amount, tier HUMAN. Never a ruling.
  G8          the Judge disagrees with the rules engine (outcome, amount, payer or payee): ESCALATE_HUMAN with reason GEN-R-ESCALATED, tier HUMAN; both
              rulings go into the case file for the reviewer (AUTH-04).
  G7          the Judge's answer failed verification again after one retry, or no valid answer came: the engine's ruling stays as the provisional
              ruling at tier APPROVE, with the engine's own explanation drafts (AUTH-04).
  ruled       the Judge and the engine agree: the engine's numbers, the Judge's citations and explanations, and the tier of tiering.py. A confidence below
              the Section 6 threshold (or TAU) makes it APPROVE: a person confirms the recommended remedy, with the full case file.
"""
from __future__ import annotations

from . import engine_stage, safety, tiering

NOTICE_G8 = ("FairRyde's automated checks did not reach one ruling on this case, so a Ryde staff member will decide it. The full case file has been prepared for the reviewer. "
             "Account history did not affect this step.")
NOTICE_G7_FALLBACK = "A recommended decision has been prepared and a Ryde staff member will review it before it takes effect."
STATUS_BY_TIER = {"AUTO": "FINAL", "APPROVE": "RECOMMENDED", "HUMAN": "ESCALATED"}


def engine_ruling(out: dict) -> dict:
    return {k: out.get(k) for k in ("outcome", "amount_sgd", "payer", "payee", "form", "reasons", "engine_tier")}


def _skeleton(out: dict) -> dict:
    return {"status": None, "outcome": None, "amount_sgd": None, "payer": None, "payee": None, "form": None, "fee_stands_sgd": out.get("fee_stands_sgd"), "tier": None,
            "tier_reasons": [], "confidence": None, "policy_sections": [], "rules": [], "evidence": [], "precedents": [], "reasoning": "", "rider_explanation": "",
            "driver_explanation": "", "explanation_source": None, "gate": None, "escalation": {"required": False, "gate": None, "reasons": []}, "agrees_with_engine": None,
            "engine_ruling": engine_ruling(out), "judge_ruling": None, "case_file_only": False, "reasons": list(out.get("reasons") or []), "section6": None}


def _judge_ruling(j: dict | None) -> dict | None:
    if not j:
        return None
    return {k: j.get(k) for k in ("outcome", "amount_sgd", "payer", "payee", "confidence", "tier", "agreement_with_engine", "disagreement_note")}


def _draft(out: dict, key: str) -> str:
    return (out.get("explanations") or {}).get(key) or NOTICE_G7_FALLBACK


def resolve_case_file(out: dict, cls, reason: str, case_file: dict | None, *, late_flag: bool = False) -> dict:
    """Safety or no engine: the result is fixed by the policy, not by the agents."""
    r = _skeleton(out)
    safety_case = reason == "SAFETY"
    r.update(status="CASE_FILE", outcome="ESCALATE_HUMAN", tier="HUMAN", case_file_only=True, gate="G4" if safety_case else "GEN-R07",
             reasons=list(out["reasons"]) or (["SE-R-HUMAN-DECIDES"] if safety_case else ["GEN-R-POLICY-GAP"]),
             rules=list(out["rules"]), explanation_source="notice", rider_explanation=safety.SAFETY_NOTICE if safety_case else safety.NO_RULE_NOTICE,
             driver_explanation=safety.SAFETY_NOTICE if safety_case else safety.NO_RULE_NOTICE,
             policy_sections=(["Section 5.1", "Section 5.2", "Section 6.2"] if safety_case and cls.profile == "organizer_v2_1" else []),
             tier_reasons=([] if late_flag else list(out["triggers"])) or (["safety: policy v2.1 Section 5.2, the agents prepare the case file only"] if safety_case else []))
    if late_flag:
        r["tier_reasons"] = ["an agent flagged safety content by meaning after the keyword check passed it; the ruling was withdrawn and the agents prepare the case file only (policy v2.1 Section 5.2)"]
    if safety_case:
        r["reasoning"] = "Safety case: the agents gathered evidence and summarized the accounts. They proposed no ruling, no finding of fault and no recommendation (policy v2.1 Section 5.2)."
    else:
        r["reasoning"] = "No written rule decides this kind of case in code (GEN-R07). A person decides; the agents summarized the accounts and the evidence."
    r["escalation"] = {"required": True, "gate": r["gate"], "reasons": r["tier_reasons"][:4] or ["a person decides"]}
    r["case_file"] = case_file
    return r


def resolve_ruling(kb, out: dict, judge: dict | None, report: dict | None, *, judge_problem: str | None = None, missing_brief: list[str] | None = None) -> dict:
    r = _skeleton(out)
    r["judge_ruling"] = _judge_ruling(judge)
    extra = []
    if missing_brief:
        extra.append(f"the {' and '.join(missing_brief)} did not return a usable brief, so the other side was not fully heard (GEN-R05): a person confirms")

    # ---- G7: no valid Judge answer
    if judge is None or report is None or (not report["ok"] and report["retryable_failure"]):
        info = tiering.tier_for_ruling(get_kb_cached(), out, None, None)
        tier = tiering.stricter(info["tier"], "APPROVE")
        why = judge_problem or (report["feedback"] if report else "no valid answer from the Judge")
        r.update(status=STATUS_BY_TIER[tier], outcome=out["outcome"], amount_sgd=out["amount_sgd"], payer=out["payer"], payee=out["payee"], form=out["form"], tier=tier,
                 gate="G7", agrees_with_engine=None, confidence=info["confidence"], section6=info["section6"], rules=list(out["rules"]), explanation_source="engine_draft",
                 rider_explanation=_draft(out, "rider"), driver_explanation=_draft(out, "driver"),
                 reasoning="The Judge's answer could not be verified (" + why + "), so the rules engine's ruling stays as the provisional ruling for a person to confirm (AUTH-04, gate G7).")
        r["tier_reasons"] = [f"G7: the Judge's answer failed verification after one retry ({why})"] + extra + info["reasons"]
        r["escalation"] = {"required": True, "gate": "G7", "reasons": r["tier_reasons"][:4]}
        return _no_ruling_to_human(r, out)

    # ---- G8: the Judge disagrees with the engine
    if report["disagrees"]:
        r.update(status="ESCALATED", outcome="ESCALATE_HUMAN", amount_sgd=None, payer=None, payee=None, tier="HUMAN", gate="G8", agrees_with_engine=False,
                 reasons=["GEN-R-ESCALATED"], rules=list(dict.fromkeys(["AUTH-04", "AUTH-06"] + list(out["rules"]))), explanation_source="notice",
                 rider_explanation=NOTICE_G8, driver_explanation=NOTICE_G8, reasoning="Gate G8 (AUTH-04): " + "; ".join(report["engine_diffs"]) + ". " + str(judge.get("reasoning") or ""),
                 evidence=list(judge.get("evidence") or []), policy_sections=list(judge.get("policy_sections") or []), precedents=list(judge.get("precedents") or []))
        r["tier_reasons"] = ["G8: the Judge disagrees with the rules engine (" + "; ".join(report["engine_diffs"]) + ")"] + extra
        r["escalation"] = {"required": True, "gate": "G8", "reasons": r["tier_reasons"]}
        return r

    # ---- agreement: the engine's ruling, the Judge's words
    info = tiering.tier_for_ruling(get_kb_cached(), out, judge.get("confidence"), judge.get("tier"))
    tier = info["tier"]
    reasons = list(info["reasons"])
    if info["below_threshold"]:
        c, s6 = info["confidence"]["final"], info["section6"]
        thr = (s6 or {}).get("threshold")
        reasons.insert(0, f"confidence {c:.2f} is below the {thr:.2f} the policy asks for: escalated to a person with the recommended ruling and the full case file" if thr else
                       f"confidence {c:.2f} is below the threshold: escalated to a person with the recommended ruling and the full case file")
    if extra:
        tier = tiering.stricter(tier, "APPROVE")
        reasons = extra + reasons
    reasons = list(dict.fromkeys(reasons))
    r.update(status=STATUS_BY_TIER[tier], outcome=out["outcome"], amount_sgd=out["amount_sgd"], payer=out["payer"], payee=out["payee"], form=out["form"],
             tier=tier, agrees_with_engine=True, confidence={**info["confidence"], "threshold": (info["section6"] or {}).get("threshold"), "below_threshold": info["below_threshold"]},
             section6=info["section6"], policy_sections=list(judge.get("policy_sections") or []), rules=list(judge.get("rules") or []), evidence=list(judge.get("evidence") or []),
             precedents=list(judge.get("precedents") or []), reasoning=str(judge.get("reasoning") or ""), rider_explanation=str(judge.get("rider_explanation") or ""),
             driver_explanation=str(judge.get("driver_explanation") or ""), explanation_source="judge", tier_reasons=reasons)
    if out["payer"] is None and out["payee"] is None and judge.get("payer"):       # the engine does not state payer and payee (engine_toll): show the Judge's, unchecked
        r["payer"], r["payee"] = engine_stage.norm_party(judge.get("payer")), engine_stage.norm_party(judge.get("payee"))
        r["payer_payee_source"] = "the Judge's reading; the engine does not state them (kb/open_items.yaml D59 (d))"
    if tier == "HUMAN":                                  # Section 6.1: above S$50 the AI agent prepares the case file only
        r = _no_ruling_to_human(r, out)
    r["escalation"] = {"required": tier != "AUTO", "gate": ("AUTH-07" if info["below_threshold"] or (info["section6"] and info["section6"]["tier"] != "AUTO") else "AUTH-02") if tier != "AUTO" else None,
                       "reasons": reasons[:5]}
    return r


def _no_ruling_to_human(r: dict, out: dict) -> dict:
    """A HUMAN tier proposes no outcome or amount (D48): the provisional ruling moves into the case file."""
    if r["tier"] == "HUMAN":
        r["provisional_ruling"] = {k: r.get(k) for k in ("outcome", "amount_sgd", "payer", "payee")}
        r.update(outcome="ESCALATE_HUMAN", amount_sgd=None, payer=None, payee=None, status="ESCALATED")
    return r


def get_kb_cached():
    from .kbaccess import get_kb
    return get_kb()

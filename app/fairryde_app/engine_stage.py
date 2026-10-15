"""Stage 3: the reference engines of kb/tools (no-show, route, toll, surge), behind one normalized result.

engines.run_case() picks the engine; this module turns its Trace or dict into plain JSON the rest of the pipeline can store, show and check.
Where the KB has no engine, the result is a GEN-R07 escalation (reason GEN-R-POLICY-GAP): no written rule decides the case in code, a person
decides with the case file. For a metered RydeTAXI route claim (FC-R00) the measurement is attached as information, never as a refund.

The engine's own approval tier (AUTH-01 to AUTH-07 under the profile) is kept as engine_tier; final_tier() in tiering.py may only raise it.
History never reaches an agent: fraud signals and their details stay in `reviewer_only`.
"""
from __future__ import annotations

import copy
import datetime as dt
import re

from .kbaccess import ORGANIZER_PROFILE, engine_toll, engines, explain, get_kb

RULING_OUTCOMES = {"PARTIAL_REFUND", "FULL_REFUND", "UPHOLD", "WAIVE_FEE", "TOLL_REFUND", "GOODWILL_CREDIT"}
NO_RULING_OUTCOMES = {"ESCALATE_HUMAN", "REQUEST_INFO"}
AMOUNT_OUTCOMES = {"PARTIAL_REFUND", "FULL_REFUND", "WAIVE_FEE", "TOLL_REFUND", "GOODWILL_CREDIT"}
PARTY_WORDS = {"RIDER": "RIDER", "DRIVER": "DRIVER", "PLATFORM": "PLATFORM", "RYDE": "PLATFORM"}


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [jsonable(v) for v in o]
    if isinstance(o, (dt.datetime, dt.date)):
        return o.isoformat()
    if o is None or isinstance(o, (bool, int, float, str)):
        return o
    return str(o)


def norm_party(x) -> str | None:
    return PARTY_WORDS.get(str(x).strip().upper()) if x else None


def _blank(profile: str, claim: str | None) -> dict:
    return {"engine": None, "profile": profile, "claim_type": claim, "outcome": None, "reasons": [], "amount_sgd": None, "payer": None, "payee": None, "form": None,
            "fee_stands_sgd": None, "rules": [], "findings": {}, "steps": [], "flags": [], "notes": [], "precedents": [], "matrix_row": None, "dt_row": None,
            "deviation_km": None, "amount_at_stake": None, "confidence": {}, "engine_tier": "HUMAN", "triggers": [], "gates": [], "decisive": [], "section6": None,
            "reclassified_to": None, "safety": False, "case_file_only": False, "case_file_reason": None, "fraud_flags": 0, "reviewer_only": {}, "explanations": {},
            "params": {}}


def no_engine_outcome(kb, canon: dict, cls) -> dict:
    """GEN-R07: no reference engine. A safety case gets SE-R-HUMAN-DECIDES instead (policy v2.1 Section 5.2)."""
    out = _blank(cls.profile, cls.claim_type)
    out["engine"] = "none"
    out["outcome"] = "ESCALATE_HUMAN"
    out["case_file_only"] = True
    out["case_file_reason"] = cls.case_file_reason or "NO_ENGINE"
    if cls.safety.get("flag"):
        out["safety"] = True
        out["reasons"] = ["SE-R-HUMAN-DECIDES"]
        out["rules"] = ["CLS-01", "SE-R01", "AUTH-03", "AUTH-06"]
        out["triggers"] = ["safety content: the AI agent may only prepare a case file (policy v2.1 Section 5.2); no outcome, amount or measure is proposed (CLS-01, SE-R01)"]
        out["steps"] = [{"rule": "CLS-01", "result": "safety content: the whole case goes to a person with the case file only"}]
    else:
        out["reasons"] = ["GEN-R-POLICY-GAP"]
        out["rules"] = ["GEN-R07", "AUTH-06"]
        out["triggers"] = [f"FairRyde has no ruling to approve (AUTH-06): no reference engine and no written rule in code for {cls.claim_type or cls.dispute_type_raw} under {cls.profile} (GEN-R07)"]
        out["steps"] = [{"rule": "GEN-R07", "result": f"no reference engine for {cls.claim_type or cls.dispute_type_raw} under {cls.profile}; escalate with the case file"}]
        trip = canon.get("trip_data") or {}
        if cls.claim_type == "FC-ROUTE" and engine_toll.is_metered(kb, trip):
            rs = canon.get("route_summary") or {}
            out["rules"] = ["FC-R00", "FC-R03", "FC-R05", "GEN-R07", "AUTH-06"]
            out["steps"] = [{"rule": "FC-R00", "result": "RydeTAXI is a metered fare: FC-R03 and FC-R05 do not apply and Ryde publishes no rule for refunding a metered fare; escalate under GEN-R07"}]
            out["findings"] = {"F-METERED-FARE": {"value": True, "rule": "FC-R00", "basis": ["E-TRP-01", "E-PAY-01"]},
                               "F-DETOUR-INFO": {"value": {"extra_distance_km": rs.get("extra_distance_km"), "extra_meter_fare_sgd": rs.get("extra_meter_fare_sgd"),
                                                           "route_agreed_in_advance": rs.get("route_agreed_in_advance"),
                                                           "traffic_feed": rs.get("traffic_incidents_on_recommended_route")},
                                                 "rule": "FC-R00", "basis": ["E-RTE-01"], "note": "information for the reviewer only, never a proposed refund"}}
    out["engine_tier"] = "HUMAN"
    out["fraud_flags"] = _fraud_flags(canon)
    return out


def _fraud_flags(canon: dict) -> int:
    from .kbaccess import P21
    return P21.fraud_flag_count(canon)


def run_engine(kb, raw_case: dict, cls, canon: dict) -> dict:
    """Run the engine that classification chose and normalize its result."""
    if cls.engine is None:
        return no_engine_outcome(kb, canon, cls)
    r = engines.run_case(kb, raw_case, cls.profile)
    res, name = r["result"], r["engine"]
    if name == "engine_toll":
        return _from_toll(kb, res, cls, canon)
    out = _from_trace(kb, res, name, cls, canon)
    if cls.route == "CASE_FILE":                      # the keyword stand-in found safety content that the engine's own profile branch rules on anyway
        out["case_file_only"], out["case_file_reason"] = True, cls.case_file_reason
        if cls.case_file_reason == "SAFETY" and not out["safety"]:
            out["safety"] = True
            out["triggers"] = ["safety content: the AI agent may only prepare a case file (policy v2.1 Section 5.2); no outcome, amount or measure is proposed (CLS-01, SE-R01)"] + out["triggers"]
            out["reasons"] = ["SE-R-HUMAN-DECIDES"]
            out["rules"] = list(dict.fromkeys(["CLS-01", "SE-R01", "AUTH-03"] + out["rules"]))
    return out


def _from_trace(kb, res: dict, name: str, cls, canon: dict) -> dict:
    t, tier = res["trace"], res["tier"]
    out = _blank(t.profile, t.claim_type or getattr(t, "case_type", None) or cls.claim_type)
    out["engine"] = name
    out["outcome"], out["reasons"] = t.outcome, list(t.reasons)
    rem = t.remedy or {}
    out["amount_sgd"] = rem.get("amount_sgd") if t.outcome in AMOUNT_OUTCOMES else None
    out["payer"], out["payee"], out["form"] = norm_party(rem.get("payer")), norm_party(rem.get("payee")), rem.get("form")
    out["fee_stands_sgd"] = rem.get("fee_stands_sgd")
    out["rules"] = list(dict.fromkeys(list(t.rules_on_path) + list(t.rules_used)))
    out["findings"] = jsonable({k: v for k, v in t.findings.items() if not k.startswith("_")})
    out["steps"] = [{"rule": s["rule"], "result": s["result"], "evidence": s["evidence"]} for s in t.steps]
    out["flags"], out["notes"] = list(t.flags), list(t.notes) + list(t.also)
    out["precedents"] = jsonable(t.precedents) if t.profile == ORGANIZER_PROFILE else []         # GEN-R08: policy v2.1 Section 7 binds the organizer profile only
    out["matrix_row"], out["dt_row"] = t.matrix_row, t.dt_row
    out["deviation_km"] = getattr(t, "deviation_km", None)
    out["amount_at_stake"] = getattr(t, "amount_at_stake", None)
    out["confidence"] = jsonable(t.confidence)
    out["engine_tier"] = tier["tier"] if tier["tier"] in ("AUTO", "APPROVE", "HUMAN") else "HUMAN"
    out["triggers"], out["gates"] = jsonable(tier.get("triggers") or []), jsonable(tier.get("gates") or [])
    out["decisive"] = jsonable(tier.get("decisive") or [])
    out["section6"] = jsonable(tier.get("section6"))
    out["reclassified_to"] = t.reclassified_to
    out["safety"] = bool(t.findings.get("_safety") or t.findings.get("_discrimination"))
    out["fraud_flags"] = _fraud_flags(canon)
    out["params"] = {k: v.get("value") for k, v in t.params_used.items()}
    out["reviewer_only"] = {"fraud_signals": jsonable(t.fraud), "fraud_detail": jsonable(getattr(t, "fraud_detail", {})),
                            "injection_authors": jsonable(t.injection_authors)}
    out["no_ruling"] = t.outcome in NO_RULING_OUTCOMES or bool(t.reclassified_to) or t.outcome not in RULING_OUTCOMES
    if out["no_ruling"]:
        out["case_file_only"] = True
        out["case_file_reason"] = "SAFETY" if out["safety"] else "NO_RULING"
    # deterministic party texts drafted from findings only (EXP-01 to EXP-03): the fallback when the Judge's text fails verification
    try:
        if t.profile == ORGANIZER_PROFILE:
            out["explanations"] = jsonable(engines.explanation(kb, res))
        elif name == "engine_noshow":                  # explain.policy_v21 adds policy v2.1 sentences (Section 2.3, Precedent 7.3) that do not belong to the Ryde profile
            out["explanations"] = jsonable(explain.noshow(kb, res))
        else:
            out["explanations"] = {}
    except Exception as exc:          # an engine without a drafting path under this profile
        out["explanations"] = {}
        out["notes"].append(f"no deterministic explanation draft ({type(exc).__name__})")
    return out


def _from_toll(kb, res: dict, cls, canon: dict) -> dict:
    out = _blank("ryde_2026", "FC-TOLL")
    out["engine"] = "engine_toll"
    out["outcome"], out["reasons"] = res["outcome"], list(res["reasons"])
    out["amount_sgd"] = res["amount"] if res["outcome"] in AMOUNT_OUTCOMES else None
    out["steps"] = [{"rule": rule, "result": text, "evidence": []} for rule, text in res["steps"]]
    out["rules"] = list(dict.fromkeys([rule for rule, _ in res["steps"] if rule in kb.rules] + ["AUTH-02"]))
    out["flags"] = list(res["flags"])
    out["engine_tier"] = res["tier"]
    out["triggers"] = jsonable(res["triggers"])
    out["decisive"] = jsonable(res["decisive"])
    out["findings"] = {"F-ERP-EXPECTED": {"value": res["expected"], "unit": "SGD", "rule": "FC-F04", "basis": ["E-ERP-01", "E-ERP-00"]},
                       "F-ERP-CHARGED": {"value": (canon.get("fare_breakdown") or {}).get("erp_toll"), "unit": "SGD", "rule": "FC-R07", "basis": ["E-PAY-01"]}}
    out["reviewer_only"] = {"fraud_signals": jsonable(res["fraud"]), "fraud_detail": {}, "injection_authors": []}
    out["fraud_flags"] = _fraud_flags(canon)
    out["notes"] = ["engine_toll returns a plain dict: payer and payee are not stated by the engine (kb/open_items.yaml D59 (d))"]
    out["no_ruling"] = res["outcome"] not in RULING_OUTCOMES
    out["explanations"] = _toll_explanations(out)
    return out


def _toll_explanations(out: dict) -> dict:
    amt, exp = out["amount_sgd"], out["findings"]["F-ERP-EXPECTED"]["value"]
    charged = out["findings"]["F-ERP-CHARGED"]["value"]
    if out["outcome"] != "TOLL_REFUND" or amt is None:
        return {}
    text = (f"The ERP gantry log shows S${exp:.2f} for this trip, and S${charged:.2f} was charged (FC-R07, E-ERP-01, E-PAY-01). The difference, S${amt:.2f}, is refunded to the rider. "
            "Account history did not affect the outcome.")
    return {"rider": text, "driver": text, "numbers_used": {"exp": f"S${exp:.2f}", "charged": f"S${charged:.2f}", "amt": f"S${amt:.2f}"}, "exp03_unmatched": []}


# ------------------------------------------------------------------ what an agent may see of an engine result
HISTORY_RULES = ("FRD-01", "FRD-02", "GEN-R03")        # fraud signals and the history rule: for the reviewer only, an agent is history-blind


def agent_rules(out: dict) -> list[str]:
    return [r for r in out["rules"] if r not in HISTORY_RULES]


def agent_steps(out: dict) -> list[dict]:
    """The engine's steps without the ones that report account history (the FRD step carries the fraud signal and its detail)."""
    return [{"rule": s["rule"], "result": s["result"]} for s in out["steps"] if not any(r in s["rule"] for r in HISTORY_RULES)]

_FRAUD_REASON = re.compile(r"a party has a fraud flag \(\d+\), so the confidence threshold is raised to (\d+%) regardless of dispute value")


def judge_view(out: dict) -> dict:
    """The engine result for the Judge: findings, steps, reasons, precedents and the Section 6 constraint, without anything about account history
    (GEN-R03: the Judge is history-blind). Fraud signals and flags are for the reviewer, not for an agent."""
    s6 = copy.deepcopy(out["section6"])
    if s6:
        s6["reasons"] = [_FRAUD_REASON.sub(r"an account-level condition (for the reviewer only) raises the confidence threshold to \1", r) for r in s6.get("reasons", [])]
        s6.pop("fraud_flags", None)
    triggers = [_FRAUD_REASON.sub(r"an account-level condition (for the reviewer only) raises the confidence threshold to \1", x)
                for x in out["triggers"] if not x.lower().startswith("fraud signal")]
    return {"engine": out["engine"], "profile": out["profile"], "claim_type": out["claim_type"], "outcome": out["outcome"], "reasons": out["reasons"],
            "amount_sgd": out["amount_sgd"], "payer": out["payer"], "payee": out["payee"], "form": out["form"], "fee_stands_sgd": out["fee_stands_sgd"],
            "rules": agent_rules(out), "matrix_row": out["matrix_row"], "decision_table_row": out["dt_row"], "findings": out["findings"],
            "steps": agent_steps(out), "flags": [f for f in out["flags"] if f != "FRAUD_SIGNAL"],
            "notes": [n for n in out["notes"] if not any(r in n for r in HISTORY_RULES) and "fraud" not in n.lower()], "deviation_km": out["deviation_km"], "engine_confidence": {k: out["confidence"].get(k) for k in ("C", "C_effective")},
            "section6": s6, "approval_triggers": triggers, "engine_tier": out["engine_tier"]}


def advocate_view(out: dict) -> dict:
    """Facts only for an advocate: the engine's findings with their evidence IDs, not its outcome, amount, tier or fraud signals."""
    return {"claim_type": out["claim_type"], "profile": out["profile"], "findings": out["findings"], "flags": [f for f in out["flags"] if f != "FRAUD_SIGNAL"],
            "relevant_rules": agent_rules(out)}

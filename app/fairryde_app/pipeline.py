"""The pipeline, end to end:

  1 intake and classification (CLS rules)        intake.py          deterministic
  2 evidence extraction with evidence IDs        evidence.py        deterministic
  3 reference engines (no-show, route, toll, surge)  engine_stage.py   deterministic (kb/tools)
  4 Rider Advocate                               agents.py          LLM
  5 Driver Advocate                              agents.py          LLM
  6 Judge                                        agents.py          LLM
  7 verifier                                     verifier.py        deterministic, one retry of the Judge
  8 approval tier (AUTH rules, profile organizer_v2_1)  tiering.py + resolve.py

run_case() returns one JSON-able record (also written to app/runs/). `emit` receives each event as it happens, so a UI can show the agents talking.
Safety (policy v2.1 Section 5) and no-engine cases run the same three agents in case file mode and end in tier HUMAN with no ruling.
"""
from __future__ import annotations

import datetime as dt
import json
import time
import uuid
from pathlib import Path

from . import agents, cases, config, engine_stage, evidence as ev, intake, llm, privacy, resolve, safety, verifier
from .kbaccess import case_adapter, get_kb


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


class Recorder:
    def __init__(self, terms, emit=None):
        self.events, self.terms, self._emit = [], terms, emit

    def __call__(self, kind: str, **data):
        event = privacy.pseudonymize({"t": _now(), "type": kind, **data}, self.terms)
        self.events.append(event)
        if self._emit:
            self._emit(event)
        return event


def run_case(case_id: str, *, mode: str | None = None, scenario: str = "normal", emit=None, save: bool = True, runs_dir: Path | None = None,
             raw_case: dict | None = None, delay_s: float = 0.0, client=None, record: bool = False) -> dict:
    t_start = time.time()
    kb = get_kb()
    info = cases.get_info(case_id) if raw_case is None else None
    raw = raw_case if raw_case is not None else cases.load_case(case_id)
    mode = mode or llm.default_mode()
    client = client or llm.make_client(mode, scenario, delay_s)
    canon, _reference = case_adapter.prepare(raw)
    terms = privacy.build_terms(canon)
    rec = Recorder(terms, emit)
    run = {"run_id": f"{dt.datetime.now():%Y%m%dT%H%M%S}-{case_id}-{client.name}-{uuid.uuid4().hex[:6]}", "case_id": case_id, "started": _now(), "mode": client.name,
           "scenario": scenario if client.name == "mock" else None, "model": config.MODEL if client.name == "live" else "mock (saved responses)",
           "app_version": "0.1.0", "kb_version": kb.version, "expected": (info.expected if info else None)}

    # ---------------------------------------------------------------- 1 intake
    rec("stage", stage="intake", status="start", title="Intake and classification (CLS rules)")
    cls = intake.classify(kb, raw, case_id, info.profile_override if info else None)
    rec("stage", stage="intake", status="end", data=cls.to_dict())

    # ---------------------------------------------------------------- 2 evidence
    rec("stage", stage="evidence", status="start", title="Evidence extraction with evidence IDs")
    items = ev.extract(kb, canon)
    rec("stage", stage="evidence", status="end", data={"items": items, "count": len(items), "withheld": [i["id"] for i in items if i["withheld"]]})

    # ---------------------------------------------------------------- 3 engines
    rec("stage", stage="engine", status="start", title="Reference engines (kb/tools)")
    out = engine_stage.run_engine(kb, raw, cls, canon)
    rec("stage", stage="engine", status="end", data=out)

    mode_ = "case_file" if out["case_file_only"] else "ruling"
    policy_text = agents.policy_context(kb, cls.profile, out, cls)
    ids = agents.valid_ids(kb, cls.profile, items, out, cls)
    run_ctx = agents.Run(case_id=case_id, kb=kb, cls=cls, items=items, out=out, mode=mode_, terms=terms, policy_text=policy_text, ids=ids)
    vctx = verifier.build_context(kb, cls.profile, items, out, policy_text)
    messages: list[dict] = []
    verification: dict = {"rider_advocate": None, "driver_advocate": None, "judge": [], "safety": None}

    def speak(agent: str, **kw) -> dict:
        title = {"rider_advocate": "Rider Advocate", "driver_advocate": "Driver Advocate", "judge": "Judge"}[agent]
        rec("stage", stage=agent, status="start", title=title)
        m = agents.call_agent(client, run_ctx, agent, **kw)
        messages.append(m)
        return m                      # the message event is emitted after the verifier has looked at it (and, on a safety case, after Section 5.2 redaction)

    # ---------------------------------------------------------------- 4 and 5 advocates
    safe_flag = {"agent": None}
    briefs: dict[str, dict | None] = {}
    checks: dict[str, dict | None] = {}
    problems: list[str] = []
    for agent, party in (("rider_advocate", "rider"), ("driver_advocate", "driver")):
        m = speak(agent, rider_brief=briefs.get("rider_advocate"))
        brief = m["json"]
        if brief is None:
            problems.append(party)
            rec("message", agent=agent, message=m)
            rec("verification", agent=agent, ok=False, checks=[{"name": "reply", "status": "FAIL", "detail": m["error"] or "no usable brief", "kind": "schema"}])
            briefs[agent], checks[agent] = None, None
            continue
        if mode_ == "case_file":
            v = verifier.verify_case_file(vctx, {"evidence": brief.get("evidence"), "case_summary": brief.get("account_summary")})
            v["lint"] = safety.lint(json.dumps(brief, ensure_ascii=False))
            brief, n = safety.redact_obj(brief)
            v["redacted_sentences"] = n
            if n:
                v["checks"].append({"name": f"{party} advocate: Section 5.2", "status": "WARN", "detail": f"{n} sentence(s) read as a ruling or recommendation and were removed", "kind": "safety"})
        else:
            v = verifier.verify_advocate(vctx, brief, party)
            if not v["ok"]:
                brief = verifier.strip_invalid(brief, v["invalid"])
        if brief.get("safety_concern") and mode_ == "ruling":
            safe_flag["agent"] = safe_flag["agent"] or agent
        briefs[agent], checks[agent], verification[agent] = brief, v, v
        m["json_shown"] = brief
        rec("message", agent=agent, message=m)
        rec("verification", agent=agent, ok=v["ok"], checks=v["checks"], invalid=v.get("invalid"))

    # a safety concern raised by an advocate by meaning: the keyword check missed it; Section 5.2 applies from here
    if safe_flag["agent"]:
        rec("notice", level="warning", text=f"The {safe_flag['agent'].replace('_', ' ')} flagged safety content that the keyword check missed. Policy v2.1 Section 5.2 applies: the ruling path is closed, the Judge prepares a case file.")
        out["case_file_only"], out["case_file_reason"] = True, "SAFETY"
        run_ctx.mode, mode_ = "case_file", "case_file"
        for a in ("rider_advocate", "driver_advocate"):
            if briefs.get(a):
                briefs[a], _n = safety.redact_obj(briefs[a])

    # ---------------------------------------------------------------- 6 and 7 judge, verifier, one retry
    judge_json, report, judge_problem, late_flag = None, None, None, False
    feedback = None
    attempt = 0
    if mode_ == "ruling":
        while True:
            m = speak("judge", attempt=attempt, rider_brief=briefs.get("rider_advocate"), driver_brief=briefs.get("driver_advocate"), retry_feedback=feedback,
                      rider_check=checks.get("rider_advocate"), driver_check=checks.get("driver_advocate"))
            rec("message", agent="judge", message=m)
            if m["json"] is None:
                judge_problem = m["error"] or "no usable answer"
                rec("verification", agent="judge", ok=False, attempt=attempt, checks=[{"name": "reply", "status": "FAIL", "detail": judge_problem, "kind": "schema"}])
                verification["judge"].append({"attempt": attempt, "ok": False, "checks": [{"name": "reply", "status": "FAIL", "detail": judge_problem, "kind": "schema"}]})
                judge_json, report = None, None
                break
            judge_json = m["json"]
            report = verifier.verify_judge(vctx, judge_json)
            verification["judge"].append({"attempt": attempt, **{k: report[k] for k in ("checks", "ok", "retryable_failure", "disagrees", "engine_diffs")}})
            rec("verification", agent="judge", attempt=attempt, ok=report["ok"], checks=report["checks"], disagrees=report["disagrees"], engine_diffs=report["engine_diffs"])
            if report["retryable_failure"] and attempt < config.JUDGE_MAX_RETRIES:
                feedback, attempt = report["feedback"], attempt + 1
                rec("notice", level="warning", text="Verification failed (" + report["feedback"] + "). The Judge is asked once to correct its answer (gate G7 if it fails again).")
                continue
            break
        if judge_json is not None and report is not None and report["safety_concern"] and not out["safety"]:
            late_flag = True
            rec("notice", level="warning", text="The Judge flagged safety content by meaning that the keyword check missed. Policy v2.1 Section 5.2: the ruling is withdrawn and the Judge prepares a case file.")
            out["case_file_only"], out["case_file_reason"] = True, "SAFETY"
            run_ctx.mode, mode_ = "case_file", "case_file"
            for a in ("rider_advocate", "driver_advocate"):
                if briefs.get(a):
                    briefs[a], _n = safety.redact_obj(briefs[a])

    case_file_json = None
    if mode_ == "case_file":
        m = speak("judge", rider_brief=briefs.get("rider_advocate"), driver_brief=briefs.get("driver_advocate"), rider_check=checks.get("rider_advocate"), driver_check=checks.get("driver_advocate"))
        if m["json"] is not None:
            v = verifier.verify_case_file(vctx, m["json"])
            lint = safety.lint(json.dumps(m["json"], ensure_ascii=False))
            case_file_json, n = safety.redact_obj(m["json"])
            if n:
                v["checks"].append({"name": "Judge case file: Section 5.2", "status": "WARN", "detail": f"{n} sentence(s) read as a ruling or recommendation and were removed", "kind": "safety"})
            v["lint"], v["redacted_sentences"] = lint, n
            verification["judge"].append({"attempt": 0, **{k: v[k] for k in ("checks", "ok")}})
            m["json_shown"] = case_file_json
            rec("message", agent="judge", message=m)
            rec("verification", agent="judge", ok=v["ok"], checks=v["checks"], invalid=v.get("invalid"))
        else:
            rec("message", agent="judge", message=m)
            rec("verification", agent="judge", ok=False, checks=[{"name": "reply", "status": "FAIL", "detail": m["error"] or "no usable case file", "kind": "schema"}])
            case_file_json = {"case_summary": "The Judge did not return a usable case file; the evidence list and the two accounts below are the case file.", "evidence": [], "open_questions": []}

    # ---------------------------------------------------------------- 8 resolution and tier
    rec("stage", stage="resolve", status="start", title="Approval tier (AUTH rules)")
    if mode_ == "case_file":
        result = resolve.resolve_case_file(out, cls, out["case_file_reason"] or "NO_ENGINE", case_file_json, late_flag=late_flag or bool(safe_flag["agent"]))
    else:
        result = resolve.resolve_ruling(kb, out, judge_json, report, judge_problem=judge_problem, missing_brief=[p + " advocate" for p in problems])
    result["case_file"] = _build_case_file(run_ctx, cls, items, out, briefs, case_file_json, judge_json, verification, result) if result["tier"] != "AUTO" else None
    rec("stage", stage="resolve", status="end", data=result)

    run.update(classification=cls.to_dict(), evidence=items, engine=out, messages=messages, briefs=briefs, verification=verification, result=result, events=rec.events,
               privacy={"terms_replaced": len(terms), "note": "names, plates, phones and account IDs are replaced before any text is sent; this log holds the pseudonymized view only"},
               finished=_now(), duration_s=round(time.time() - t_start, 2), expected_check=compare_expected(info.expected if info else None, result))
    rec("final", result={k: result.get(k) for k in ("status", "outcome", "amount_sgd", "tier")})
    for e in rec.events:                       # the stage payloads are already in the record (classification, evidence, engine, result): keep the log lean
        if e["type"] == "stage":
            e.pop("data", None)
    run = privacy.pseudonymize(run, terms)
    if record and client.name == "live":
        run["recorded_fixture"] = str(record_fixture(case_id, messages, terms))
    if save:
        run["log_file"] = str(save_run(run, runs_dir))
    return run


def _build_case_file(run_ctx, cls, items, out, briefs, case_file_json, judge_json, verification, result) -> dict:
    """What a human reviewer gets: everything, in one place (the record of the run holds the same items; this is the one-page index plus the full material)."""
    return {"case_id": run_ctx.case_id, "why_escalated": result["escalation"], "tier": result["tier"], "classification": cls.to_dict(), "engine_ruling": result["engine_ruling"],
            "judge_ruling": result["judge_ruling"], "provisional_ruling": result.get("provisional_ruling"), "engine": {k: v for k, v in out.items() if k != "explanations"},
            "reviewer_only": out["reviewer_only"], "evidence": items, "rider_advocate_brief": briefs.get("rider_advocate"), "driver_advocate_brief": briefs.get("driver_advocate"),
            "judge_answer": judge_json, "judge_case_file": case_file_json, "verification": verification,
            "note": "Account history (fraud signals and flags) is in reviewer_only and was never shown to an agent."}


def compare_expected(expected: dict | None, result: dict) -> dict | None:
    if not expected:
        return None
    want_amt = expected.get("amount_sgd")
    got_amt = result.get("amount_sgd")
    amt_ok = (want_amt is None and got_amt in (None, 0, 0.0)) or (want_amt is not None and got_amt is not None and abs(got_amt - want_amt) < 0.005)
    out_ok = result["outcome"] == expected["outcome"]
    tier_ok = expected.get("tier") is None or result["tier"] == expected["tier"]
    return {"outcome_ok": out_ok, "amount_ok": amt_ok, "tier_ok": tier_ok, "ok": out_ok and amt_ok and tier_ok, "expected": expected}


def record_fixture(case_id: str, messages: list[dict], terms) -> Path:
    """Keep what the model really said (the last reply of each agent and mode) as the saved responses for mock mode."""
    path = config.MOCK_DIR / f"{case_id}.json"
    fx = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"case_id": case_id, "responses": {}}
    for m in messages:
        if m.get("json") is not None and not m.get("error"):
            key = m["agent"] if m["mode"] == "ruling" else f"{m['agent']}:{m['mode']}"
            fx["responses"][key] = privacy.pseudonymize(m["json"], terms)
    fx.update(source="recorded from a live run", model=config.MODEL, recorded=_now(), note="Recorded model answers (pseudonymized).")
    config.MOCK_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fx, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def save_run(run: dict, runs_dir: Path | None = None) -> Path:
    d = Path(runs_dir or config.RUNS_DIR)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{run['run_id']}.json"
    path.write_text(json.dumps(run, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def load_run(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

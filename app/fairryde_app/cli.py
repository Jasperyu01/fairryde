"""Run a case from the command line and print the conversation.

    python -m fairryde_app.cli DISP-001                 # mock mode if ANTHROPIC_API_KEY is not set, else live
    python -m fairryde_app.cli DISP-001 --mock --scenario judge_disagrees
    python -m fairryde_app.cli DISP-002 --live --record # call the model, keep its answers as the saved responses
    python -m fairryde_app.cli --list
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap

from . import cases, llm, pipeline

WIDTH = 110


def _wrap(text: str, indent: str = "    ") -> str:
    return textwrap.fill(str(text), WIDTH, initial_indent=indent, subsequent_indent=indent)


def print_run(run: dict, out=sys.stdout) -> None:
    p = lambda *a: print(*a, file=out)
    c = run["classification"]
    p(f"\n=== {run['case_id']}  ({run['mode']} mode{', scenario ' + run['scenario'] if run.get('scenario') else ''}, profile {c['profile']}) ===")
    p(f"[1 intake]   {c['claim_type']} ({c['claim_label']}); route {c['route']}" + (f" ({c['case_file_reason']})" if c["case_file_reason"] else ""))
    p(f"[2 evidence] {len(run['evidence'])} items; withheld: {', '.join(i['id'] for i in run['evidence'] if i['withheld'])}")
    e = run["engine"]
    p(f"[3 engine]   {e['engine']}: {e['outcome']} amount {e['amount_sgd']} engine tier {e['engine_tier']}; reasons {', '.join(e['reasons'])}")
    for m in run["messages"]:
        j = m.get("json_shown") or m.get("json") or {}
        p(f"\n[{m['role']}{' (retry)' if m['attempt'] else ''}] {m['model']}  {m['latency_s']}s")
        if m.get("error"):
            p(_wrap("ERROR: " + m["error"]))
            continue
        for key in ("stance", "brief", "account_summary", "case_summary", "reasoning"):
            if j.get(key):
                p(_wrap(j[key]))
                break
        if m["agent"] == "judge" and j.get("outcome"):
            p(_wrap(f"-> {j['outcome']} amount {j.get('amount_sgd')} confidence {j.get('confidence')} tier {j.get('tier')}"))
    for v in run["verification"]["judge"]:
        bad = [x for x in v["checks"] if x["status"] in ("FAIL", "WARN")]
        p(f"[verifier]   attempt {v['attempt']}: " + ("all checks pass" if not bad else "; ".join(f"{x['status']} {x['detail']}" for x in bad)))
    r = run["result"]
    p(f"\n[RESULT]     {r['status']}: {r['outcome']}  amount {r['amount_sgd']}  tier {r['tier']}  gate {r['gate']}")
    if r["confidence"]:
        p(f"             confidence {r['confidence']['final']} (Judge {r['confidence']['judge']}, engine {r['confidence']['engine']})")
    for t in r["tier_reasons"][:4]:
        p(_wrap("why: " + t, "             "))
    p(_wrap("to the rider:  " + r["rider_explanation"], "             "))
    p(_wrap("to the driver: " + r["driver_explanation"], "             "))
    if run.get("expected_check"):
        ec = run["expected_check"]
        p(f"[expected]   {ec['expected']['outcome']} {ec['expected']['amount_sgd']} {ec['expected']['tier']}  ->  {'OK' if ec['ok'] else 'DIFFERS'}")
    if run.get("log_file"):
        p(f"[log]        {run['log_file']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case", nargs="?")
    ap.add_argument("--live", action="store_true", help="call the Anthropic API (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--mock", action="store_true", help="replay the saved responses")
    ap.add_argument("--scenario", default="normal", choices=list(llm.MOCK_SCENARIOS))
    ap.add_argument("--record", action="store_true", help="live only: keep the model's answers as the saved responses")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--json", action="store_true", help="print the run record as JSON")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    if a.list or not a.case:
        for i in cases.list_cases():
            print(f"{i.case_id:15s} {i.kind:10s} {i.dispute_type:16s} expected {i.expected.get('outcome')} {i.expected.get('amount_sgd')} {i.expected.get('tier')}")
        return 0
    mode = "live" if a.live else "mock" if a.mock else llm.default_mode()
    run = pipeline.run_case(a.case, mode=mode, scenario=a.scenario, save=not a.no_save, record=a.record)
    print(json.dumps(run, indent=1, ensure_ascii=False)) if a.json else print_run(run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

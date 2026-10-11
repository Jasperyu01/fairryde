"""Rerun the reference engine on round 1 end-to-end cases and compare with the settled references (a regression check, DEP: E).

    python3 validation/tools/rerun_engine.py OUT.json E01 E02 E03 E04 E11

Reads validation/V4_e2e/cases/<id>.json and validation/V4_e2e/42_reference.jsonl; writes one record per case to OUT.json.
No-show cases run on kb/tools/engine_noshow.py; an ERP case (dispute_type erp_toll, such as E11) runs on kb/tools/engine_toll.py
and must also match the reference amount.
Round 1 cases are no longer held out (the fixer has seen them), so this is a regression check, never a validation score.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kb" / "tools"))

from kbload import KB             # noqa: E402
import engine_noshow as E         # noqa: E402
import engine_toll as ET          # noqa: E402

if __name__ == "__main__":
    out_path, ids = Path(sys.argv[1]), sys.argv[2:]
    ref = {}
    for line in open(ROOT / "validation/V4_e2e/42_reference.jsonl", encoding="utf-8"):
        d = json.loads(line)
        ref[d["case_id"]] = d
    kb, rows = KB(), []
    for cid in ids:
        case = json.load(open(ROOT / f"validation/V4_e2e/cases/{cid}.json", encoding="utf-8"))
        want = ref[cid]["reference_outcome"]
        human = ref[cid].get("labeler", {}).get("human")
        if case["dispute_ticket"]["dispute_type"] == "erp_toll":
            r = ET.run(kb, case)
            amt = ref[cid].get("reference_amount")
            rows.append({"case_id": cid, "reference_outcome": want, "reference_amount": amt, "kb_outcome": r["outcome"], "kb_amount": r["amount"],
                         "dt_row": None, "tier": r["tier"], "correct": r["outcome"] == want and (amt is None or r["amount"] == amt),
                         "route_match": (r["tier"] == "HUMAN") == bool(human), "reasons": r["reasons"], "fraud": r["fraud"],
                         "decisive": [f"{a}: {b}" for a, b in r["decisive"]], "triggers": r["triggers"]})
            continue
        r = E.run(kb, case)
        t, tier = r["trace"], r["tier"]
        rows.append({"case_id": cid, "reference_outcome": want, "kb_outcome": t.outcome, "dt_row": t.dt_row, "tier": tier["tier"],
                     "correct": t.outcome == want, "route_match": (tier["tier"] == "HUMAN") == bool(human),
                     "rider_evidence": t.findings.get("F-RIDER-EVIDENCE", {}).get("value"),
                     "rider_contacts": (getattr(t, "rider_contact_detail", None) or {}).get("readings", {}),
                     "decisive": [f"{a}: {b}" for a, b in tier["decisive"]], "triggers": tier["triggers"]})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for x in rows:
        print(("OK   " if x["correct"] and x["route_match"] else "DIFF ") + x["case_id"], x["reference_outcome"], "->", x["kb_outcome"], x["dt_row"], x["tier"])
    print(f"{sum(x['correct'] for x in rows)}/{len(rows)} outcomes match; written to {out_path}")

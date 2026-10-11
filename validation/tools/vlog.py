"""Run log for the validation (who did what, when, with which inputs and outputs). One JSON line per event.

    python3 vlog.py start P2 E builder "draw seeded samples"
    python3 vlog.py end   P2 "rules 23, ontology 14" out1 out2 ...
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent / "run_log.jsonl"
SGT = timezone(timedelta(hours=8))


def log(event: dict):
    event = {"time": datetime.now(SGT).isoformat(timespec="seconds"), **event}
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


if __name__ == "__main__":
    kind = sys.argv[1]
    if kind == "start":
        _, _, step, dep, actor, *what = sys.argv
        print(log({"event": "start", "step": step, "dep": dep, "actor": actor, "what": " ".join(what)}))
    elif kind == "end":
        _, _, step, result, *outputs = sys.argv
        print(log({"event": "end", "step": step, "result": result, "outputs": outputs}))
    else:
        print(log({"event": kind, "note": " ".join(sys.argv[2:])}))

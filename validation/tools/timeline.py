"""Timeline of the validation run from run_log.jsonl: one row per primitive with actor, D/E, start, end and minutes.

    python3 timeline.py            # prints the table and writes V5_scorecard/53_timeline.json

Use it to see where the time went and which step was the bottleneck of each wave (the run log is append-only, so the same
script also works while a run is in progress: open steps show as RUNNING).
"""
import json
from datetime import datetime
from pathlib import Path

V = Path(__file__).resolve().parent.parent
events = [json.loads(l) for l in (V / "run_log.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
t = lambda s: datetime.fromisoformat(s)

steps, notes = {}, []
for e in events:
    if e["event"] == "start":
        steps[e["step"]] = {"step": e["step"], "dep": e["dep"], "actor": e["actor"], "what": e["what"], "start": e["time"],
                            "end": None, "result": None}
    elif e["event"] == "end":
        s = steps.setdefault(e["step"], {"step": e["step"], "dep": "?", "actor": "?", "what": "", "start": e["time"]})
        s["end"], s["result"] = e["time"], e["result"]
    else:
        notes.append({"time": e["time"], "note": e.get("note")})

rows = []
for s in steps.values():
    mins = round((t(s["end"]) - t(s["start"])).total_seconds() / 60, 1) if s["end"] else None
    rows.append({**s, "minutes": mins, "status": "DONE" if s["end"] else "RUNNING"})
rows.sort(key=lambda r: r["start"])
first, last = t(rows[0]["start"]), max(t(r["end"]) for r in rows if r["end"])
wall = round((last - first).total_seconds() / 60, 1)
agent = round(sum(r["minutes"] or 0 for r in rows if r["dep"] == "D"), 1)
script = round(sum(r["minutes"] or 0 for r in rows if r["dep"] == "E"), 1)
out = {"wall_minutes": wall, "sum_of_D_step_minutes": agent, "sum_of_E_step_minutes": script,
       "parallelism": round(agent / wall, 2) if wall else None, "steps": rows, "notes": notes}
(V / "V5_scorecard/53_timeline.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))

print(f"{'step':6} {'D/E':3} {'actor':22} {'start':8} {'end':8} {'min':>5}  result")
for r in rows:
    print(f"{r['step']:6} {r['dep']:3} {r['actor']:22} {r['start'][11:19]:8} {(r['end'] or '')[11:19]:8} {r['minutes'] if r['minutes'] is not None else '':>5}  {(r['result'] or r['status'])[:70]}")
print(f"wall {wall} min; D steps {agent} agent-min; E steps {script} min; parallelism {out['parallelism']}")

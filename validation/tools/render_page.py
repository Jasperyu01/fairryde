"""V5.4 (execution): render the scorecard page from the checkpoint files. No judgment happens here.

    python3 render_page.py   ->  V5_scorecard/55_scorecard_page.html

Rerun after a new validation round and the page shows the new numbers.
"""
import html
import json
from datetime import datetime, timedelta
from pathlib import Path

V = Path(__file__).resolve().parent.parent
OUT = V / "V5_scorecard/55_scorecard_page.html"


def lines(rel):
    return [json.loads(l) for l in (V / rel).read_text(encoding="utf-8").splitlines() if l.strip()]


def clean(s):
    s = "" if s is None else str(s)
    return s.replace(" — ", ", ").replace("—", ", ").replace("–", "-")


def e(s):
    return html.escape(clean(s))


sc = json.loads((V / "V5_scorecard/51_scorecard.json").read_text())
integ = json.loads((V / "V5_scorecard/52_integrity.json").read_text())
tl = json.loads((V / "V5_scorecard/53_timeline.json").read_text())
fx = json.loads((V / "V5_scorecard/54_fix_list.json").read_text())
M = sc["metrics"]

CHIP = {"GOOD": "good", "ACCEPTABLE": "ok", "BAD": "bad", "PASS": "good", "CORRECT": "good", "INCORRECT": "bad",
        "CRITICAL": "bad", "MAJOR": "ok", "MINOR": "minor", "UNCOVERED": "ok", "WRONG_CLASS": "bad", "UNSUPPORTED": "bad",
        "WRONG_RELATION": "bad", "CONFLICT": "bad", "MISSING_EXCEPTION": "bad", "OVERGENERALIZED": "bad",
        "TOO_HIGH": "ok", "TOO_LOW": "minor", "OK": "plain"}


def chip(text, kind=None):
    if not text:
        return '<span class="none">none</span>'
    k = kind or CHIP.get(str(text), "plain")
    return f'<span class="chip {k}">{e(str(text).replace("_", " "))}</span>'


# ------------------------------------------------------------------ metric interval charts
DEFS = {
    "M1": "Share of 20 real complaint texts whose KB label is the right taxonomy leaf.",
    "M2": "Share of 14 sampled ontology items (entities, roles, relations, events) that the sources show as defined.",
    "M3": "Share of 20 randomly drawn rules whose every element is in its cited source or openly labeled an assumption.",
    "M4": "Share of the 34 rules and ontology items judged UNSUPPORTED or CONFLICT. Lower is better.",
    "M5": "Share of 15 held-out cases where the KB's decision equals the settled reference outcome (amount within S$0.05).",
}


def fnum(v):
    return f"{v:.2f}".rstrip("0").rstrip(".") if v not in (0, 1) else str(int(v))


def interval_svg(key, m):
    lower = key == "M4"
    top = 0.5 if lower else 1.0
    x0, x1 = 16, 584

    def X(v):
        return x0 + min(max(v, 0), top) / top * (x1 - x0)
    g = float(m["thresholds"]["good"].split()[1])
    a = float(m["thresholds"]["acceptable"].split()[1])
    zones = ([(0, g, "zg"), (g, a, "zo"), (a, top, "zb")] if lower else [(0, a, "zb"), (a, g, "zo"), (g, top, "zg")])
    parts = [f'<svg viewBox="0 0 600 64" class="ivl" role="img" aria-label="{e(m["name"])}: {m["rate"]:.3f}, 95% interval {m["wilson95"][0]} to {m["wilson95"][1]}">']
    for lo, hi, cls in zones:
        parts.append(f'<rect class="{cls}" x="{X(lo):.1f}" y="18" width="{X(hi) - X(lo):.1f}" height="16" rx="2"/>')
    ticks = sorted({0, a, g, top})
    for t in ticks:
        parts.append(f'<line class="tk" x1="{X(t):.1f}" x2="{X(t):.1f}" y1="34" y2="40"/>')
        anchor = "start" if t == 0 else ("end" if t == top else "middle")
        parts.append(f'<text class="tl" x="{X(t):.1f}" y="54" text-anchor="{anchor}">{fnum(t)}</text>')
    lo, hi = m["wilson95"]
    parts.append(f'<line class="ci" x1="{X(lo):.1f}" x2="{X(hi):.1f}" y1="26" y2="26"/>')
    for v in (lo, hi):
        parts.append(f'<line class="ci" x1="{X(v):.1f}" x2="{X(v):.1f}" y1="20" y2="32"/>')
    parts.append(f'<circle class="pt" cx="{X(m["rate"]):.1f}" cy="26" r="6"/>')
    lx = X(m["rate"])
    anchor = "middle" if 40 < lx < 560 else ("start" if lx <= 40 else "end")
    parts.append(f'<text class="pv" x="{lx:.1f}" y="12" text-anchor="{anchor}">{m["rate"]:.3f}</text>')
    parts.append("</svg>")
    return "".join(parts)


def supp(key, m):
    s = m.get("supplementary", {})
    if key == "M1":
        return (f"Coverage {s['coverage']:.2f} (2 texts need a leaf the taxonomy lacks). The blind judge picked the same leaf on "
                f"{s['blind_judge_vs_kb_same_primary'].replace('/', ' of ')} texts. One text (C08) has the right leaf but is routed away from safety triage.")
    if key == "M2":
        return "Failures: O08 drop-off cardinality (CRITICAL); O09 and O10 are design relations with no source or design label (MINOR)."
    if key == "M3":
        st = m["by_credibility_stratum"]
        return (f"By credibility stratum: A {st['A']}, B {st['B']}, C {st['C']}, D {st['D']}. Weighted to the 87-rule KB: "
                f"{s['post_stratified_kb_level_estimate']:.3f} (roughly {s['post_stratified_approx_95'][0]:.2f} to {s['post_stratified_approx_95'][1]:.2f}), just above the acceptable line.")
    if key == "M4":
        c = s["critical_or_major_only"]
        return (f"Of the 7, 3 are CRITICAL (CW-F04, FC-R08, FRD-02) and 4 MINOR. Counting only CRITICAL or MAJOR gives "
                f"{c['num']} of {c['den']} = {c['rate']:.3f}. M4 reuses M2 and M3 failures, so it is not an independent signal.")
    if key == "M5":
        return (f"Same human-versus-automatic route on all 11 correct cases; the safety case reached a person. "
                f"Of the 4 errors, 3 send a case to a person that the policy would decide (safe direction) and 1 proposes a refund the policy does not support (unsafe).")
    return ""


metric_rows = []
for key in ("M1", "M2", "M3", "M4", "M5"):
    m = M[key]
    metric_rows.append(f"""
  <div class="mrow">
    <div class="mname"><span class="mkey">{key}</span><h3>{e(m['name'])}</h3><p class="def">{e(DEFS[key])}</p></div>
    <div class="mval"><span class="big">{m['rate']:.2f}</span><span class="frac">{m['num']} of {m['den']}</span>{chip(m['status'])}</div>
    <div class="mchart">{interval_svg(key, m)}<p class="supp">{e(supp(key, m))}</p></div>
  </div>""")

# ------------------------------------------------------------------ decision checks
d = sc["decision"]
ck = d["checks"]
checks = [
    ("All five metrics at least acceptable", ck["metrics_bad"] == 0, f"{ck['metrics_bad']} below the line (M2, M3, M4)"),
    ("At least three metrics good", ck["metrics_good"] >= 3, f"{ck['metrics_good']} good (M1)"),
    ("No CRITICAL finding on the DISP-002 path (decision-table row R8)", not ck["critical_findings_on_DISP002_path"],
     "CW-F04 is UNSUPPORTED and CRITICAL. DISP-002's own outcome and approval tier do not change."),
    ("No systematic issue (the same failure twice or more in one layer)", ck["systematic_issues"] == 0,
     f"{ck['systematic_issues']} patterns, {ck['systematic_critical']} of them CRITICAL"),
]
check_rows = "".join(f'<tr><td>{e(a)}</td><td>{chip("met" if ok else "not met", "good" if ok else "bad")}</td><td>{e(n)}</td></tr>' for a, ok, n in checks)
labels = {"registered": "As registered", "M3_post_stratified": "M3 weighted to the whole KB",
          "M3_post_stratified_and_M2_design_allowed": "...and design relations allowed in the ontology",
          "all_three_lenient_readings": "...and M4 counting only CRITICAL or MAJOR"}
rob_rows = "".join(
    f'<tr><td>{e(labels[k])}</td>' + "".join(f'<td>{chip(v["statuses"][mk])}</td>' for mk in ("M1", "M2", "M3", "M4", "M5")) +
    f'<td>{chip(v["verdict"].replace("_", "-"), "bad" if v["verdict"] == "NO_GO" else "ok")}</td></tr>'
    for k, v in d["robustness"].items())

# ------------------------------------------------------------------ fix list
fix_rows = []
for it in fx["items"]:
    changes = "".join(f"<li>{e(c)}</li>" for c in it["change"])
    fix_rows.append(f"""
  <article class="fix">
    <div class="fixhead"><span class="fid">{it['id']}</span><span class="prio p{it['priority']}">priority {it['priority']}</span>{chip(it['severity'])}<span class="dir">{e(it['direction'])}</span></div>
    <h3>{e(it['title'])}</h3>
    <p>{e(it['problem'])}</p>
    <ul class="chg">{changes}</ul>
    <p class="from"><span>Verify:</span> {e(it['verify'])}</p>
    <p class="from"><span>From:</span> {e('; '.join(it['from']))}</p>
  </article>""")

# ------------------------------------------------------------------ layer tables
cases = {r["case_id"]: r for r in lines("V1_taxonomy/10_cases.jsonl")}
kbl = {r["case_id"]: r for r in lines("V1_taxonomy/11_labels_kb.jsonl")}
bl = {r["case_id"]: r for r in lines("V1_taxonomy/12_labels_judge_blind.jsonl")}
tax_rows = "".join(
    f'<tr><td class="id">{r["case_id"]}</td><td>{e(cases[r["case_id"]]["platform"])}, {e(cases[r["case_id"]]["party"])}</td>'
    f'<td class="id">{e(kbl[r["case_id"]]["primary_type"])}</td><td class="id">{e(bl[r["case_id"]]["primary_type"])}</td>'
    f'<td>{chip(r["verdict"])}</td><td>{chip(r["severity"]) if r["severity"] else ""}</td>'
    f'<td>{"" if r.get("is_dispute_ok") is not False else chip("routing wrong", "bad")}</td>'
    f'<td class="why">{e(r["reason"])} <a href="{e(cases[r["case_id"]]["source_url"])}" rel="noopener" target="_blank">source</a></td></tr>'
    for r in lines("V1_taxonomy/13_verdicts.jsonl"))
ont_rows = "".join(
    f'<tr><td class="id">{r["item_id"]}</td><td class="id">{e(r["label"])}</td><td>{chip(r["verdict"])}</td>'
    f'<td>{chip(r["severity"]) if r["severity"] else ""}</td><td class="why">{e(r["reason"])}</td></tr>'
    for r in lines("V2_ontology/21_verdicts.jsonl"))
cp_ids = {c["rule_id"] for c in sc["critical_path_detail"]}
WHO = {"V3.1a": "reviewer a", "V3.1b": "reviewer b", "V3.2 adjudication": "adjudicator (a and b disagreed)"}
rule_list = sc["rules_detail"] + [c | {"stratum": c.get("credibility_label") + " (path)"} for c in sc["critical_path_detail"]
                                  if c["rule_id"] not in {r["rule_id"] for r in sc["rules_detail"]}]
rule_rows = "".join(
    f'<tr><td class="id">{r["rule_id"]}{" <span class=tag>R8 path</span>" if r["rule_id"] in cp_ids else ""}</td>'
    f'<td>{e(r.get("credibility_label") or r["stratum"])}</td><td>{chip(r["verdict"])}</td>'
    f'<td>{chip(r["severity"]) if r["severity"] else ""}</td><td>{chip(r["credibility_check"]) if r.get("credibility_check") != "OK" else "ok"}</td>'
    f'<td>{e(WHO.get(r["source"], r["source"]))}</td><td class="why">{e(r["reason"])}</td></tr>'
    for r in rule_list)
SIT = {"E01": "No-show fee; rider's message: still getting ready", "E02": "No-show fee; driver tapped I'm Here 630 m away",
       "E03": "No-show fee; rider messaged '1 min', driver cancelled at 3 min 15 s", "E04": "No-show fee; trip carries its own 6 and 10 minute policy",
       "E05": "Rider cancellation after the ETA jumped from 4 to 9 minutes", "E06": "Advance booking cancelled 17.5 minutes before pick-up",
       "E07": "Waiting fee; rider messaged 'coming down, 2 min'", "E08": "Waiting fee; driver tapped I'm Here 370 m away",
       "E09": "Long-way complaint on a fixed RydeX fare", "E10": "Detour on a metered RydeTAXI cash fare",
       "E11": "ERP keyed in at S$8.50, one gantry at S$2.50", "E12": "Driver's cleaning claim: photos and the rider's admission",
       "E13": "Harassment report (safety)", "E14": "Lost iPad reported after 24 hours", "E15": "Driver appeals a 1-star rating"}
adj4 = {r["case_id"]: r for r in lines("V4_e2e/45_adjudication.jsonl")}


def money(v):
    return f" S${v:.2f}" if v else ""


e2e_rows = "".join(
    f'<tr><td class="id">{c["case_id"]}</td><td>{e(SIT[c["case_id"]])}</td>'
    f'<td class="id">{e(c["reference_outcome"])}{money(c["reference_amount"])}</td>'
    f'<td class="id">{e(c["kb_outcome"])}{money(c["kb_amount"])}<br><span class="sub">tier {e(c["kb_tier"])}, {"engine" if c["route"] == "engine" else "agent"}</span></td>'
    f'<td>{chip(c["verdict"])}</td>'
    f'<td class="why">{e(adj4[c["case_id"]]["cause"] + ", " + adj4[c["case_id"]]["direction"] + " direction: " + adj4[c["case_id"]]["reason"]) if c["case_id"] in adj4 else ""}</td></tr>'
    for c in lines("V4_e2e/44_comparison.jsonl"))

# ------------------------------------------------------------------ timeline chart
steps = [s for s in tl["steps"] if s["end"]]
t0 = datetime.fromisoformat(steps[0]["start"]).replace(second=0)
t0 = t0.replace(minute=t0.minute - t0.minute % 15)
tend = max(datetime.fromisoformat(s["end"]) for s in steps)
span = (tend - t0).total_seconds() / 60
span = (int(span // 15) + 1) * 15
LX, RX, RH, TOP = 150, 590, 17, 22
H = TOP + RH * len(steps) + 26


def tx(t):
    return LX + ((datetime.fromisoformat(t) - t0).total_seconds() / 60) / span * (RX - LX)


svg = [f'<svg viewBox="0 0 600 {H}" class="tline" role="img" aria-label="Timeline of the validation primitives">']
for k in range(0, span + 1, 15):
    x = LX + k / span * (RX - LX)
    lab = (t0 + timedelta(minutes=k)).strftime("%H:%M")
    svg.append(f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="{TOP - 6}" y2="{H - 22}"/>')
    svg.append(f'<text class="tl" x="{x:.1f}" y="{H - 8}" text-anchor="middle">{lab}</text>')
for i, s in enumerate(steps):
    y = TOP + i * RH
    a, b = tx(s["start"]), tx(s["end"])
    svg.append(f'<text class="rl" x="4" y="{y + 11}">{e(s["step"])} <tspan class="ra">{e(s["actor"].replace("_", " "))}</tspan></text>')
    svg.append(f'<rect class="{"bd" if s["dep"] == "D" else "be"}" x="{a:.1f}" y="{y + 2}" width="{max(b - a, 2.5):.1f}" height="{RH - 6}" rx="2"/>')
    if s["minutes"] and s["minutes"] >= 8:
        svg.append(f'<text class="bl" x="{b + 4:.1f}" y="{y + 11}">{s["minutes"]:.0f} min</text>')
svg.append(f'<text class="tl" x="{LX}" y="12">D = an agent judges</text><rect class="bd" x="{LX + 108}" y="4" width="14" height="9" rx="2"/>'
           f'<text class="tl" x="{LX + 136}" y="12">E = a script executes</text><rect class="be" x="{LX + 252}" y="4" width="14" height="9" rx="2"/>')
svg.append("</svg>")

ev = sc["evidence_traceability"]
n_sys_crit = ck["systematic_critical"]

page = f"""<title>FairRyde KB v0.1 Scorecard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&display=swap">
<style>
/* Layout: one reading column (1080px max). Summary first (decision, five metric rows with interval bars), then the fix list,
   then every verdict in disclosure tables, then the run log. Inspection-sheet feel: cool grey ground, petrol ink, semantic
   green/amber/red kept apart from the accent. */
:root {{
  --bg: #F2F4F2; --surface: #FFFFFF; --ink: #16201C; --muted: #56645E; --line: #D6DDD8; --accent: #1C5870;
  --good: #22744A; --good-bg: #DCEEE3; --ok: #925E0E; --ok-bg: #F5E7CB; --bad: #AD252D; --bad-bg: #F6DADC;
  --minor-bg: #E7EBE9; --zg: #CBE5D5; --zo: #F1DFB9; --zb: #F0CDD0; --bar-d: #1C5870; --bar-e: #8C9A94;
  --font-display: "Archivo", "Helvetica Neue", Arial, sans-serif;
  --font-body: "Source Sans 3", "Segoe UI", Roboto, Arial, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #101513; --surface: #182019; --ink: #E3EAE6; --muted: #9AA9A2; --line: #2A3430; --accent: #7DBDD3;
  --good: #66C792; --good-bg: #17331F; --ok: #E4B05A; --ok-bg: #3A2C12; --bad: #F2828A; --bad-bg: #3F1C20;
  --minor-bg: #252E2A; --zg: #1C3A29; --zo: #3B3017; --zb: #3F2226; --bar-d: #7DBDD3; --bar-e: #5F6D67; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #101513; --surface: #182019; --ink: #E3EAE6; --muted: #9AA9A2; --line: #2A3430; --accent: #7DBDD3;
  --good: #66C792; --good-bg: #17331F; --ok: #E4B05A; --ok-bg: #3A2C12; --bad: #F2828A; --bad-bg: #3F1C20;
  --minor-bg: #252E2A; --zg: #1C3A29; --zo: #3B3017; --zb: #3F2226; --bar-d: #7DBDD3; --bar-e: #5F6D67; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--ink); font-family: var(--font-body); font-size: 15.5px; line-height: 1.5; }}
.wrap {{ max-width: 1080px; margin: 0 auto; padding-inline: 20px; padding-block: 28px 64px; display: grid; gap: 40px; }}
h1, h2, h3 {{ font-family: var(--font-display); text-wrap: balance; margin: 0; }}
h1 {{ font-size: clamp(28px, 4.2vw, 40px); font-weight: 700; letter-spacing: -0.01em; line-height: 1.1; }}
h2 {{ font-size: 21px; font-weight: 600; margin-bottom: 4px; }}
h3 {{ font-size: 16px; font-weight: 600; }}
p {{ margin: 0; }}
a {{ color: var(--accent); }}
a:focus-visible, summary:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.eyebrow {{ font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }}
.lede {{ color: var(--muted); max-width: 68ch; }}
header {{ display: grid; gap: 14px; }}
.verdict {{ display: grid; grid-template-columns: auto 1fr; gap: 18px; align-items: center; background: var(--surface);
  border: 1px solid var(--line); border-left: 6px solid var(--bad); border-radius: 6px; padding: 18px 20px; }}
.verdict .tag-big {{ font-family: var(--font-display); font-weight: 700; font-size: 30px; color: var(--bad); letter-spacing: 0.02em; }}
.verdict p {{ max-width: 70ch; }}
.facts {{ display: flex; flex-wrap: wrap; gap: 8px 18px; font-size: 13.5px; color: var(--muted); }}
.facts b {{ color: var(--ink); font-weight: 600; font-variant-numeric: tabular-nums; }}
section {{ display: grid; gap: 14px; min-width: 0; }}
.mrows {{ display: grid; gap: 0; background: var(--surface); border: 1px solid var(--line); border-radius: 6px; }}
.mrow {{ display: grid; grid-template-columns: minmax(0, 1.05fr) 120px minmax(0, 1.6fr); gap: 18px; padding: 16px 18px; border-top: 1px solid var(--line); align-items: start; }}
.mrow:first-child {{ border-top: 0; }}
.mkey {{ font-family: var(--font-mono); font-size: 12px; color: var(--muted); }}
.def {{ font-size: 13.5px; color: var(--muted); margin-top: 2px; }}
.mval {{ display: grid; gap: 2px; justify-items: start; }}
.big {{ font-family: var(--font-display); font-size: 30px; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1; }}
.frac {{ font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums; margin-bottom: 4px; }}
.mchart {{ min-width: 0; }}
.supp {{ font-size: 13.5px; color: var(--muted); margin-top: 2px; }}
svg {{ display: block; width: 100%; height: auto; }}
.ivl .zg {{ fill: var(--zg); }} .ivl .zo {{ fill: var(--zo); }} .ivl .zb {{ fill: var(--zb); }}
.ivl .tk {{ stroke: var(--muted); stroke-width: 1; }}
.ivl .ci {{ stroke: var(--ink); stroke-width: 2; }}
.ivl .pt {{ fill: var(--ink); stroke: var(--surface); stroke-width: 2; }}
.tl, .pv {{ fill: var(--muted); font-family: var(--font-mono); font-size: 11px; }}
.pv {{ fill: var(--ink); font-weight: 500; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 13px; color: var(--muted); }}
.sw {{ display: inline-block; width: 12px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }}
.chip {{ display: inline-block; font-family: var(--font-mono); font-size: 11.5px; font-weight: 500; letter-spacing: 0.02em; padding: 1px 7px;
  border-radius: 3px; white-space: nowrap; background: var(--minor-bg); color: var(--ink); }}
.chip.good {{ background: var(--good-bg); color: var(--good); }} .chip.ok {{ background: var(--ok-bg); color: var(--ok); }}
.chip.bad {{ background: var(--bad-bg); color: var(--bad); }} .chip.minor {{ background: var(--minor-bg); color: var(--muted); }}
.none {{ color: var(--muted); }}
.panel {{ background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px; display: grid; gap: 12px; min-width: 0; }}
.scroll {{ overflow-x: auto; min-width: 0; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; }}
th {{ text-align: left; font-weight: 600; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; padding: 6px 8px; border-bottom: 1px solid var(--line); white-space: nowrap; }}
td {{ padding: 8px; border-bottom: 1px solid var(--line); vertical-align: top; }}
tr:last-child td {{ border-bottom: 0; }}
td.id {{ font-family: var(--font-mono); font-size: 12.5px; white-space: nowrap; }}
td.why {{ min-width: 280px; color: var(--ink); }}
.sub {{ color: var(--muted); font-family: var(--font-body); font-size: 12px; }}
.tag {{ font-family: var(--font-mono); font-size: 10.5px; color: var(--accent); border: 1px solid var(--accent); border-radius: 3px; padding: 0 4px; margin-left: 4px; }}
.fixes {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 330px), 1fr)); gap: 12px; }}
.fix {{ background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 14px 16px; display: grid; gap: 8px; align-content: start; min-width: 0; }}
.fixhead {{ display: flex; flex-wrap: wrap; gap: 6px 8px; align-items: center; }}
.fid {{ font-family: var(--font-mono); font-weight: 500; font-size: 13px; color: var(--accent); }}
.prio {{ font-size: 12px; color: var(--muted); }}
.prio.p1 {{ color: var(--ink); font-weight: 600; }}
.dir {{ font-size: 12px; color: var(--muted); }}
.fix p {{ font-size: 14px; }}
.chg {{ margin: 0; padding-left: 18px; font-size: 13.5px; display: grid; gap: 3px; }}
.from {{ font-size: 12.5px; color: var(--muted); }}
.from span {{ font-weight: 600; color: var(--ink); }}
details {{ background: var(--surface); border: 1px solid var(--line); border-radius: 6px; }}
summary {{ cursor: pointer; padding: 12px 16px; display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: baseline; list-style: none; }}
summary::-webkit-details-marker {{ display: none; }}
summary::before {{ content: "+"; font-family: var(--font-mono); color: var(--accent); width: 12px; }}
details[open] summary::before {{ content: "-"; }}
summary h3 {{ font-size: 15.5px; }}
summary .cnt {{ font-size: 13px; color: var(--muted); }}
details .scroll {{ padding: 0 8px 10px; }}
.tline .grid {{ stroke: var(--line); stroke-width: 1; }}
.tline .rl {{ fill: var(--ink); font-family: var(--font-mono); font-size: 10.5px; }}
.tline .ra {{ fill: var(--muted); }}
.tline .bl {{ fill: var(--muted); font-family: var(--font-mono); font-size: 10px; }}
.tline .bd {{ fill: var(--bar-d); }} .tline .be {{ fill: var(--bar-e); }}
.tline-box {{ min-width: 560px; }}
ul.plain {{ margin: 0; padding-left: 18px; display: grid; gap: 6px; max-width: 80ch; }}
.stack {{ display: grid; gap: 14px; min-width: 0; }}
.wrap > *, details, .panel, .stack > * {{ min-width: 0; }}
.two {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 14px; }}
footer {{ font-size: 13px; color: var(--muted); display: grid; gap: 6px; border-top: 1px solid var(--line); padding-top: 16px; }}
code {{ font-family: var(--font-mono); font-size: 12.5px; }}
@media (max-width: 760px) {{
  .mrow {{ grid-template-columns: 1fr auto; }}
  .mrow .mchart {{ grid-column: 1 / -1; }}
  .verdict {{ grid-template-columns: 1fr; gap: 8px; }}
}}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
</style>

<main class="wrap">
<header>
  <p class="eyebrow">Independent validation &middot; Ryde track &middot; 7 Oct 2026</p>
  <h1>FairRyde KB v0.1 Scorecard</h1>
  <p class="lede">Five pre-registered metrics decide whether the knowledge base is ready for agent building. Reviewers were fresh agents that never saw the KB being built; each step saved its own output and logged its time.</p>
  <div class="verdict">
    <div class="tag-big">NO-GO</div>
    <p>Three of five metrics fall below the acceptable line and {n_sys_crit} failure patterns repeat at CRITICAL severity, so v0.1 should not be the agent's decision base as it stands. The failures are concentrated: seven fixes (FX1 to FX7) cover every CRITICAL finding, after which the same validation is re-run with doubled samples.</p>
  </div>
  <div class="facts">
    <span>Plan hashed before any result: <b>{integ['plan_sha256'][:12]}</b></span>
    <span>KB files unchanged: <b>{integ['kb_files_checked']} of {integ['kb_files_checked']}</b></span>
    <span>Evidence quotes found in their sources: <b>{ev['verified_in_cited_file'] + ev['found_in_another_source_file']} of {ev['quotes_checked']}</b></span>
    <span>Run time: <b>{tl['wall_minutes']:.0f} min</b> wall, {tl['sum_of_D_step_minutes']:.0f} agent-min in parallel</span>
  </div>
</header>

<section id="metrics">
  <h2>Five metrics against the thresholds</h2>
  <div class="legend"><span><i class="sw" style="background:var(--zg)"></i>good</span><span><i class="sw" style="background:var(--zo)"></i>acceptable</span><span><i class="sw" style="background:var(--zb)"></i>bad</span><span>dot = rate, whiskers = Wilson 95% interval</span></div>
  <div class="mrows">{''.join(metric_rows)}
  </div>
</section>

<section id="decision">
  <h2>Why the rule says NO-GO</h2>
  <div class="stack">
    <div class="panel">
      <h3>GO needs all four</h3>
      <div class="scroll"><table><thead><tr><th>Condition</th><th>Result</th><th>Detail</th></tr></thead><tbody>{check_rows}</tbody></table></div>
      <p class="supp">NO-GO applies when two or more metrics are bad, or when a CRITICAL failure is systematic. Both hold.</p>
    </div>
    <div class="panel">
      <h3>The verdict under lenient readings</h3>
      <div class="scroll"><table><thead><tr><th>Reading</th><th>M1</th><th>M2</th><th>M3</th><th>M4</th><th>M5</th><th>Verdict</th></tr></thead><tbody>{rob_rows}</tbody></table></div>
      <p class="supp">M2, M3 and M4 share failures, so they are not three independent votes. The verdict does not rest on that: the repeated CRITICAL patterns give NO-GO under every reading.</p>
    </div>
  </div>
</section>

<section id="fixes">
  <h2>Fix list for v0.2</h2>
  <p class="lede">Grouped by the builder from the reviewers' verdicts (a synthesis, not a new verdict). Priority 1 covers every CRITICAL finding; priority 2 and 3 can follow.</p>
  <div class="fixes">{''.join(fix_rows)}
  </div>
</section>

<section id="layers">
  <h2>Every verdict</h2>
  <details><summary><h3>Taxonomy</h3><span class="cnt">20 real complaint texts &middot; 18 PASS &middot; 2 UNCOVERED &middot; KB label vs the judge's blind label</span></summary>
    <div class="scroll"><table><thead><tr><th>Case</th><th>Platform, filer</th><th>KB label</th><th>Blind label</th><th>Verdict</th><th>Severity</th><th>Routing</th><th>Judge's reason</th></tr></thead><tbody>{tax_rows}</tbody></table></div></details>
  <details><summary><h3>Ontology</h3><span class="cnt">14 sampled items &middot; 11 PASS &middot; 1 CRITICAL</span></summary>
    <div class="scroll"><table><thead><tr><th>Item</th><th>KB element</th><th>Verdict</th><th>Severity</th><th>Reviewer's reason</th></tr></thead><tbody>{ont_rows}</tbody></table></div></details>
  <details><summary><h3>Rules</h3><span class="cnt">20 random (A 6, B 4, C 3, D 7) plus 2 on the DISP-002 path &middot; 13 of 20 PASS &middot; 4 CRITICAL</span></summary>
    <div class="scroll"><table><thead><tr><th>Rule</th><th>Credibility</th><th>Verdict</th><th>Severity</th><th>Label check</th><th>Decided by</th><th>Reason</th></tr></thead><tbody>{rule_rows}</tbody></table></div></details>
  <details><summary><h3>End to end</h3><span class="cnt">15 held-out cases &middot; 11 CORRECT &middot; references from two policy-only agents that agreed on all 15</span></summary>
    <div class="scroll"><table><thead><tr><th>Case</th><th>Situation</th><th>Reference</th><th>KB decision</th><th>Verdict</th><th>Adjudicated cause</th></tr></thead><tbody>{e2e_rows}</tbody></table></div></details>
</section>

<section id="run">
  <h2>How the run went</h2>
  <div class="panel">
    <div class="scroll"><div class="tline-box">{''.join(svg)}</div></div>
    <p class="supp">{tl['wall_minutes']:.0f} minutes of wall time against a 60-minute plan. Two agent steps set the pace: writing the 15 cases (48 min) and applying the KB to 11 of them (33 min). Every primitive wrote a start and an end line to <code>run_log.jsonl</code>; <code>tools/timeline.py</code> turns that log into this chart.</p>
  </div>
</section>

<section id="limits" class="two">
  <div class="panel">
    <h3>Limits of this validation</h3>
    <ul class="plain">
      <li>Samples are small, so the intervals are wide. The decision rests on repeated CRITICAL patterns more than on any single rate.</li>
      <li>The end-to-end references come from two AI agents that read only Ryde's texts. They agreed on all 15, which also suggests the cases were cleaner than real disputes. A person should check the four mismatches.</li>
      <li>On the two rules both reviewers saw, they disagreed once (CW-F04), so single-reviewer verdicts carry noise.</li>
      <li>CLS-03 passed the rule review, but the taxonomy layer exposed its safety gap (C08). Counting it, M3 would be 12 of 20.</li>
      <li>A strong model applied the KB with plenty of time. The production agent may apply it less faithfully; that is a separate test.</li>
      <li>The builder pre-registered the plan. Its hash was recorded before any result and is unchanged.</li>
    </ul>
  </div>
  <div class="panel">
    <h3>Re-validation after the fixes</h3>
    <ul class="plain">{''.join(f'<li>{e(c)}</li>' for c in fx['revalidation']['changes'])}
      <li>Same verdict definitions, metrics and thresholds; the plan is hashed again before results.</li>
    </ul>
  </div>
</section>

<footer>
  <p>Checkpoints: <code>00_freeze.json</code>, <code>01_plan.yaml</code>, <code>V1_taxonomy/</code>, <code>V2_ontology/</code>, <code>V3_rules/</code>, <code>V4_e2e/</code>, <code>V5_scorecard/</code>, <code>run_log.jsonl</code>. Prompts for every agent are in <code>prompts/</code>; scripts in <code>tools/</code>.</p>
  <p>Integrity checked {e(integ['checked_at'][:16].replace('T', ' '))} SGT. Generated by <code>tools/render_page.py</code>.</p>
</footer>
</main>
"""
OUT.write_text(page, encoding="utf-8")
bad = [ch for ch in ("—", "–") if ch in page]
print(OUT, len(page), "bytes", "| dashes:", bad or "none")

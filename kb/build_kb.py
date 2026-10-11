#!/usr/bin/env python3
"""Build and verify the FairRyde knowledge base.

    python3 build_kb.py            # checks + DISP-002 evaluation + self-test + GPS fuzz + privacy + reports + both workbooks
    python3 build_kb.py --no-xlsx  # skip the workbooks
    python3 build_kb.py --no-fuzz  # skip the randomized GPS check (tools/fuzz_presence.py; run it alone for more cases)

Exit code 1 if any ERROR is found. Prints counts only for anything privacy-related (ONT.11).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "tools"))

from kbload import KB  # noqa: E402
import checks  # noqa: E402
import engine_noshow  # noqa: E402
import explain  # noqa: E402
import fuzz_presence  # noqa: E402
import privacy_scan  # noqa: E402
import report_md  # noqa: E402
import selftest  # noqa: E402
import stats  # noqa: E402

RECALC = Path("/mnt/skills/public/xlsx/scripts/recalc.py")     # LibreOffice recalculation, when available


def recalc(path: Path) -> dict:
    if not RECALC.exists():
        return {"status": "skipped (recalc script not available on this machine)"}
    p = subprocess.run([sys.executable, str(RECALC), str(path), "120"], capture_output=True, text=True, timeout=300)
    text = p.stdout.strip()
    try:
        return json.loads(text[text.index("{"): text.rindex("}") + 1])
    except ValueError:
        return {"status": "error", "stdout": text[-500:], "stderr": p.stderr[-500:]}


def main(argv):
    kb = KB(HERE)
    cases = {"DISP-002": kb.disp002}
    rep = checks.run_all(kb, set(engine_noshow.evidence_index(kb.disp002, kb)), cases)
    runs = {prof: engine_noshow.run(kb, kb.disp002, prof) for prof in ("organizer_case", "ryde_2026")}
    dt_enum = engine_noshow.dt_enumeration(kb)
    priv = privacy_scan.dry_run(kb.disp002)
    if not priv["clean"]:
        rep.add("ERROR", "privacy", "DISP-002", "pseudonymization dry run left identifiers (see counts)")

    # engine self-test, its coverage, and the number check of every explanation draft (EXP-03)
    tests = selftest.run(kb)
    for t in tests:
        if not t["ok"]:
            rep.add("ERROR", "engine-selftest", t["id"], "; ".join(t["problems"]))
    reading_bad = selftest.reading_check()
    for x in reading_bad:
        rep.add("ERROR", "reading-selftest", x["text"][:40], f"CW-F06 message reading expected {x['expected']}, got {x['got']}"
                + (" (unsafe: a placing or contesting message read as no counter-evidence)" if x["unsafe"] else ""))
    decided = {t["got"]["row"] for t in tests if t["got"]["row"] and t["got"]["reasons"]
               and t["got"]["reasons"][0] not in ("CW-R-OUT-OF-WINDOW", "GEN-R-POLICY-GAP")}
    for row in kb.y["rules"]["decision_tables"]["DT-CW-NOSHOW"]["rows"]:
        if row["row"] not in decided:
            rep.add("ERROR", "selftest-coverage", row["row"], "no self-test variant is decided by this decision-table row")
    for tier in kb.vocab["TX-TIER-AUTONOMY"]:
        if tier not in {t["got"]["tier"] for t in tests}:
            rep.add("ERROR", "selftest-coverage", tier, "no self-test variant reaches this autonomy tier")
    for g in ("G1", "G4", "G6"):
        if not any(any(x.startswith(g) for x in t["gates"]) for t in tests):
            rep.add("ERROR", "selftest-coverage", g, "no self-test variant fires this gate")
    for vid, desc, case, exp, prof in selftest.variants(kb.disp002):
        run_v = engine_noshow.run(kb, case, prof)
        ex = explain.noshow(kb, run_v)
        if ex["exp03_unmatched"]:
            rep.add("ERROR", "exp03", vid, f"explanation numbers not registered as findings: {ex['exp03_unmatched']}")
        tv = run_v["trace"]                     # every code the engine emits must exist in the taxonomy (layer convergence)
        for f in tv.flags:
            if f not in kb.vocab["TX-FLAG"]:
                rep.add("ERROR", "engine-codes", vid, f"flag {f} is not in TX-FLAG")
        for rc in tv.reasons:
            if rc not in kb.vocab["TX-REASON"]:
                rep.add("ERROR", "engine-codes", vid, f"reason {rc} is not in TX-REASON")
        if tv.outcome and tv.outcome not in kb.vocab["TX-OUTCOME"]:
            rep.add("ERROR", "engine-codes", vid, f"outcome {tv.outcome} is not in TX-OUTCOME")
        if not tv.reclassified_to and run_v["tier"]["tier"] not in kb.vocab["TX-TIER-AUTONOMY"]:
            rep.add("ERROR", "engine-codes", vid, f"tier {run_v['tier']['tier']} is not in TX-TIER-AUTONOMY")
        for rid in tv.rules_on_path + tv.rules_used:
            if rid not in kb.rules:
                rep.add("ERROR", "engine-codes", vid, f"rule {rid} on the trace does not exist")
        statuses = next(a["type"] for a in kb.entities["ENT-FINDING"]["attributes"] if a["name"] == "status").split(" | ")
        for code, fd in tv.findings.items():
            if code.startswith("_"):
                continue
            if code not in kb.findings:
                rep.add("ERROR", "engine-codes", vid, f"finding {code} is not a finding type in the ontology")
            elif fd["status"] not in statuses:
                rep.add("ERROR", "engine-codes", vid, f"finding {code} has status {fd['status']}, not in ENT-FINDING.status")
            allowed = kb.findings.get(code, {}).get("values")
            if isinstance(allowed, str):            # a vocabulary id, for example TX-BOOKING
                allowed = list(kb.vocab.get(allowed, {}))
            if allowed and fd["value"] is not None and str(fd["value"]) not in [str(v) for v in allowed]:
                rep.add("ERROR", "engine-codes", vid, f"finding {code} = {fd['value']} is not one of its values {allowed}")

    fuzz = None
    if "--no-fuzz" not in argv:           # randomized GPS check: no automatic ruling may rest on GPS that leaves the question open
        fuzz = fuzz_presence.run(kb, 150, 7)
        for b in fuzz[3]:
            rep.add("ERROR", "gps-fuzz", f"case {b[0]}", str(b[1])[:200])

    out = HERE / "out"
    out.mkdir(exist_ok=True)
    terms = privacy_scan.dictionary(kb.disp002)
    ann_status = {"message": "workbooks skipped (--no-xlsx)"}
    files = []
    if "--no-xlsx" not in argv:
        import make_xlsx
        ann_path = out / "FairRyde_Annotation_v0.1.xlsx"
        ann_status = make_xlsx.build_annotation(kb, ann_path, [privacy_scan.pseudonymize(kb.disp002, terms)])
        if ann_status.get("written"):
            rc = recalc(ann_path)
            ann_status["recalc"] = rc
            if rc.get("status") == "errors_found" or rc.get("error"):
                rep.add("ERROR", "xlsx-formulas", ann_path.name, f"recalculation: {rc}")
        kb_path = out / "FairRyde_KB_v0.1.xlsx"
        kb_status = make_xlsx.build_kb_workbook(kb, rep, runs, dt_enum, priv, tests, kb_path, ann_status)
        files = [kb_path, ann_path]

    (out / "disp002_trace.md").write_text(report_md.trace_report(kb, runs), encoding="utf-8")
    (out / "check_report.md").write_text(report_md.check_report(kb, rep, runs, dt_enum, priv, tests, None, ann_status), encoding="utf-8")

    # leak scan of everything generated (ONT.11.4): dictionary terms, identifier patterns and name fragments, counts only
    allow = {a for a in kb.articles} | set(re.findall(r"\d{9,}", json.dumps(kb.corpus.get("section_listings", {}))))
    strings = []
    for f in files:
        if f.exists():
            strings += privacy_scan.xlsx_strings(f)
    for f in ("check_report.md", "disp002_trace.md"):
        strings.append((out / f).read_text(encoding="utf-8"))
    for f in sorted(HERE.glob("*.yaml")):          # our own files too; sources/ keeps the organizer's original
        if f.name != "privacy.yaml":
            strings.append(f.read_text(encoding="utf-8"))
    out_scan = privacy_scan.output_scan(strings, terms, allow, dictionary_only=[(HERE / "privacy.yaml").read_text(encoding="utf-8")])
    if out_scan["total"]:
        rep.add("ERROR", "privacy-outputs", "out/", f"generated outputs contain identifiers (counts only): {out_scan}")
    if files:       # second pass: the summary sheet now shows the leak-scan result and the final error count
        kb_status = make_xlsx.build_kb_workbook(kb, rep, runs, dt_enum, priv, tests, kb_path, ann_status, out_scan)
        rescan = privacy_scan.output_scan(privacy_scan.xlsx_strings(kb_path), terms, allow)
        if rescan["total"] and not out_scan["total"]:
            rep.add("ERROR", "privacy-outputs", kb_path.name, f"the regenerated workbook contains identifiers (counts only): {rescan}")
    (out / "check_report.md").write_text(report_md.check_report(kb, rep, runs, dt_enum, priv, tests, out_scan, ann_status), encoding="utf-8")

    st = stats.compute(kb, rep, priv)
    print(f"rules {len(kb.rules)} | vocabularies {len(kb.vocab)} | entities {len(kb.entities)} | events {st['n_events']} | playbooks {len(kb.playbooks)}")
    print(f"quotes: {st['n_quotes_verified']} verified, {st['n_quotes_bad']} not verifiable, {st['n_quotes_total']} sources in total")
    for prof, r in runs.items():
        t = r["trace"]
        print(f"DISP-002 [{prof}]: {t.outcome} via {t.dt_row}, reasons {t.reasons}, flags {t.flags}, C={t.confidence['C']}, tier {r['tier']['tier']}")
    print(f"DT-CW-NOSHOW enumeration: {dt_enum}")
    print(f"engine self-test: {sum(t['ok'] for t in tests)}/{len(tests)} variants pass; rows decided by self-tests: {sorted(decided, key=lambda s: int(s[1:]))}")
    n_read = len(selftest.READING_CASES) + len(selftest.reading_corpus())
    print(f"CW-F06 message readings: {n_read - len(reading_bad)}/{n_read} pass (exact cases and the reviewers' corpus)")
    if fuzz:
        print(f"GPS fuzz (seed 7): {fuzz[0]} random cases, {fuzz[1]} automatic, {fuzz[2]} crashes, {len(fuzz[3])} findings")
    print(f"privacy dry run (counts only): before {priv['before']} after {priv['after']} fragments {priv['fragments_after']} clean={priv['clean']}")
    print(f"leak scan of outputs (counts only): {out_scan}")
    print(f"annotation workbook: {ann_status.get('message')} {ann_status.get('recalc', '')}")
    if files:
        print(f"knowledge-base workbook: {kb_status}")
    print(f"ERROR {rep.count('ERROR')} | WARN {rep.count('WARN')} | INFO {rep.count('INFO')}")
    for lvl in ("ERROR", "WARN"):
        for i in rep.issues:
            if i.level == lvl:
                print(f"  {lvl:5} {i.check:20} {i.item:28} {i.message}")
    return 1 if rep.count("ERROR") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

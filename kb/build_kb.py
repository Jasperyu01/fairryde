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
import kbload  # noqa: E402
import engine_noshow  # noqa: E402
import case_adapter  # noqa: E402
import engines  # noqa: E402
import explain  # noqa: E402
import fuzz_presence  # noqa: E402
import privacy_scan  # noqa: E402
import report_md  # noqa: E402
import selftest  # noqa: E402
import selftest_v21  # noqa: E402
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
    cases = dict(kb.organizer_cases)                       # DISP-001, DISP-002 and DISP-003: the organizer's samples
    rep = checks.run_all(kb, set(engine_noshow.evidence_index(kb.disp002, kb)), cases)
    # DISP-002 under the default profile (organizer_v2_1), the legacy profile that reads its embedded object, and the Ryde profile
    runs = {prof: engine_noshow.run(kb, kb.disp002, prof) for prof in ("organizer_v2_1", "organizer_case", "ryde_2026")}
    org_runs = {cid: engines.run_case(kb, case)["result"] for cid, case in kb.organizer_cases.items()}      # the three samples through the dispatcher
    dt_enum = engine_noshow.dt_enumeration(kb)
    priv = privacy_scan.dry_run_all(list(kb.organizer_cases.values()))
    if not priv["clean"]:
        rep.add("ERROR", "privacy", "organizer cases", "pseudonymization dry run left identifiers (see counts)")

    # engine self-test, its coverage, and the number check of every explanation draft (EXP-03)
    tests = selftest.run(kb)
    for t in tests:
        if not t["ok"]:
            rep.add("ERROR", "engine-selftest", t["id"], "; ".join(t["problems"]))
    reading_bad = selftest.reading_check()
    for x in reading_bad:
        rep.add("ERROR", "reading-selftest", x["text"][:40], f"CW-F06 message reading expected {x['expected']}, got {x['got']}"
                + (" (unsafe: a placing or contesting message read as no counter-evidence)" if x["unsafe"] else ""))
    a2_bad = selftest.erp_check(kb) + selftest.erp_code_check(kb) + selftest.g3_check(kb) + selftest.rule_card_check(kb) + selftest.a3_check(kb) + selftest.a4_check(kb)
    for x in a2_bad:
        rep.add("ERROR", "erp-g3-selftest", x["id"], f"{x['variant']}: " + "; ".join(x["problems"]))
    erp_line = (f"ERP rules self-test: {len(selftest.erp_cases())} ERP cases, the FC-R01 split, gate G3, the A2, A3 and A4 rule-card checks and the census: "
                + ("all pass" if not a2_bad else f"{len(a2_bad)} problem(s)"))
    v21 = selftest_v21.run(kb)                  # step A6: the organizer samples pinned to their expected rulings, variants, regression, reconciliation records
    for x in v21:
        if not x["ok"]:
            rep.add("ERROR", "v21-selftest", x["id"], x["variant"][:70] + ": " + "; ".join(x["problems"]))
    v21_line = (f"Policy v2.1 self-test (A6): {sum(x['ok'] for x in v21)}/{len(v21)} pass (the three organizer samples pinned to their expected rulings, one-factor variants, "
                "tolls pass-through, regression E01 to E04 and E11, and the reconciliation records)")
    erp_line = erp_line + "\n* " + v21_line
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
    def check_trace_codes(vid, tv, tier_name):
        """Every code an engine emits must exist in the taxonomy and the ontology (layer convergence)."""
        for f in tv.flags:
            if f not in kb.vocab["TX-FLAG"]:
                rep.add("ERROR", "engine-codes", vid, f"flag {f} is not in TX-FLAG")
        for rc in tv.reasons:
            if rc not in kb.vocab["TX-REASON"]:
                rep.add("ERROR", "engine-codes", vid, f"reason {rc} is not in TX-REASON")
        if tv.outcome and tv.outcome not in kb.vocab["TX-OUTCOME"]:
            rep.add("ERROR", "engine-codes", vid, f"outcome {tv.outcome} is not in TX-OUTCOME")
        if not tv.reclassified_to and tier_name not in kb.vocab["TX-TIER-AUTONOMY"]:
            rep.add("ERROR", "engine-codes", vid, f"tier {tier_name} is not in TX-TIER-AUTONOMY")
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
        for st in tv.steps:                         # every rule a step names exists (the step's rule field lists IDs and 'or' / ranges)
            for rid in kbload.expand_rule_refs(st["rule"]):
                if rid not in kb.rules and rid not in kb.y["rules"].get("decision_tables", {}) and not rid.startswith("E-"):
                    rep.add("ERROR", "engine-codes", vid, f"step {st['playbook']} {st['n']} names rule {rid}, which does not exist")

    for vid, desc, case, exp, prof in selftest.variants(kb.disp002):
        run_v = engine_noshow.run(kb, case, prof or ("organizer_case" if case.get("cancellation_policy") else "ryde_2026"))
        ex = explain.noshow(kb, run_v)
        if ex["exp03_unmatched"]:
            rep.add("ERROR", "exp03", vid, f"explanation numbers not registered as findings: {ex['exp03_unmatched']}")
        check_trace_codes(vid, run_v["trace"], run_v["tier"]["tier"])
    for cid, res in org_runs.items():              # the three organizer samples under organizer_v2_1, with the explanations that cite the policy sections
        ex = explain.policy_v21(kb, res)
        if ex["exp03_unmatched"]:
            rep.add("ERROR", "exp03", cid, f"explanation numbers not registered as findings: {ex['exp03_unmatched']}")
        check_trace_codes(cid, res["trace"], res["tier"]["tier"])
    for vid, desc, case, exp in selftest_v21.variants(kb):
        if "overrides" not in exp:
            res = engines.run_case(kb, case)["result"]
            check_trace_codes(vid, res["trace"], res["tier"]["tier"])

    fuzz = None
    if "--no-fuzz" not in argv:           # randomized GPS check: no automatic ruling may rest on GPS that leaves the question open
        fuzz = fuzz_presence.run(kb, 150, 7)                       # the default profile (organizer_v2_1 for these DISP-002 based cases)
        for prof in ("organizer_case", "ryde_2026"):               # A6 round 1: the other profiles keep the guard
            more = fuzz_presence.run(kb, 100, 7, prof)
            fuzz = (fuzz[0] + more[0], fuzz[1] + more[1], fuzz[2] + more[2], fuzz[3] + more[3])
        for b in fuzz[3]:
            rep.add("ERROR", "gps-fuzz", f"case {b[0]}", str(b[1])[:200])

    out = HERE / "out"
    out.mkdir(exist_ok=True)
    terms = privacy_scan.dictionary_all(list(kb.organizer_cases.values()))
    ann_status = {"message": "workbooks skipped (--no-xlsx)"}
    files = []
    if "--no-xlsx" not in argv:
        import make_xlsx
        ann_path = out / f"FairRyde_Annotation_{kb.vtag}.xlsx"
        ann_cases = []
        for case in kb.organizer_cases.values():          # the three organizer samples, each pseudonymized with its own dictionary, without the organizer's own answer blocks
            canon, _ref = case_adapter.prepare(case)
            ann_cases.append(privacy_scan.pseudonymize(canon, privacy_scan.dictionary(case)))
        ann_status = make_xlsx.build_annotation(kb, ann_path, ann_cases)
        if ann_status.get("written"):
            rc = recalc(ann_path)
            ann_status["recalc"] = rc
            if rc.get("status") == "errors_found" or rc.get("error"):
                rep.add("ERROR", "xlsx-formulas", ann_path.name, f"recalculation: {rc}")
        kb_path = out / f"FairRyde_KB_{kb.vtag}.xlsx"
        kb_status = make_xlsx.build_kb_workbook(kb, rep, runs, dt_enum, priv, tests, kb_path, ann_status, None, org_runs)
        files = [kb_path, ann_path]

    (out / "disp002_trace.md").write_text(report_md.trace_report(kb, runs), encoding="utf-8")
    (out / "check_report.md").write_text(report_md.check_report(kb, rep, runs, dt_enum, priv, tests, None, ann_status, erp_line), encoding="utf-8")

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
        kb_status = make_xlsx.build_kb_workbook(kb, rep, runs, dt_enum, priv, tests, kb_path, ann_status, out_scan, org_runs)
        rescan = privacy_scan.output_scan(privacy_scan.xlsx_strings(kb_path), terms, allow)
        if rescan["total"] and not out_scan["total"]:
            rep.add("ERROR", "privacy-outputs", kb_path.name, f"the regenerated workbook contains identifiers (counts only): {rescan}")
    (out / "check_report.md").write_text(report_md.check_report(kb, rep, runs, dt_enum, priv, tests, out_scan, ann_status, erp_line), encoding="utf-8")

    st = stats.compute(kb, rep, priv)
    print(f"rules {len(kb.rules)} | vocabularies {len(kb.vocab)} | entities {len(kb.entities)} | events {st['n_events']} | playbooks {len(kb.playbooks)}")
    print(f"quotes: {st['n_quotes_verified']} verified, {st['n_quotes_bad']} not verifiable, {st['n_quotes_total']} sources in total")
    for prof, r in runs.items():
        t = r["trace"]
        print(f"DISP-002 [{prof}]: {t.outcome} via {t.dt_row}, reasons {t.reasons}, flags {t.flags}, C={t.confidence['C']}, tier {r['tier']['tier']}")
    for cid in ("DISP-001", "DISP-003"):
        r = org_runs[cid]
        t = r["trace"]
        print(f"{cid} [{t.profile}]: {t.outcome} S${(t.remedy or {}).get('amount_sgd')}, reasons {t.reasons}, flags {t.flags}, C={t.confidence['C']}, tier {r['tier']['tier']}")
    for cid, r in org_runs.items():
        sc = engines.score(kb, cid, r)
        print(f"  expected ruling of {cid}: {'matches' if sc['ok'] else 'DIFFERS ' + str(sc['problems'])}")
        if not sc["ok"]:
            rep.add("ERROR", "organizer-expected", cid, "; ".join(sc["problems"]))
    print(f"DT-CW-NOSHOW enumeration: {dt_enum}")
    print(f"engine self-test: {sum(t['ok'] for t in tests)}/{len(tests)} variants pass; rows decided by self-tests: {sorted(decided, key=lambda s: int(s[1:]))}")
    print(erp_line.replace("\n* ", "\n"))
    n_read = len(selftest.READING_CASES) + len(selftest.BEFORE_ARRIVAL_CASES) + len(selftest.reading_corpus())
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

"""Markdown reports written by build_kb.py into kb/out/."""
from __future__ import annotations

from collections import Counter

import explain


def _tbl(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x).replace("|", "/").replace("\n", " ") for x in r) + " |")
    return "\n".join(out)


def check_report(kb, rep, runs, dt_enum, priv, tests, out_scan=None, ann_status=None) -> str:
    lines = ["# FairRyde knowledge base v0.1: check report", "",
             f"Generated from the YAML source files (knowledge base dated {kb.y['rules']['meta']['updated']}).", ""]
    lines.append(f"* Rules: {len(kb.rules)}; vocabularies: {len(kb.vocab)}; TX-CASE leaves: {len(kb.case_leaves)}; "
                 f"entities: {len(kb.entities)}; events: {len(kb.y['ontology']['events'])}; playbooks: {len(kb.playbooks)}")
    st = Counter(q["status"] for q in rep.quotes)
    lines.append(f"* Rule sources: {len(rep.quotes)}; " + ", ".join(f"{k} {v}" for k, v in st.most_common()))
    cr = Counter(r["credibility"] for r in rep.credibility)
    md = Counter(kb.rules[r]["mode"] for r in kb.rules)
    lines.append("* Credibility: " + ", ".join(f"{k} {cr[k]}" for k in "ABCD") + "; modes: " + ", ".join(f"{k} {v}" for k, v in md.items()))
    lines.append(f"* DISP-002 fields mapped: {len(rep.tables['disp002_mapping'])} of {rep.tables['disp002_leaf_count']} leaf paths")
    lines.append(f"* DT-CW-NOSHOW enumeration: {dt_enum}")
    lines.append(f"* State machines: {rep.tables.get('state_machines')}")
    lines.append(f"* Engine self-test: {sum(t['ok'] for t in tests)}/{len(tests)} variants pass")
    lines.append(f"* Privacy dry run on DISP-002 (counts only): before {priv['before']}; after {priv['after']}; fragments after {priv['fragments_after']}; clean {priv['clean']}")
    if out_scan is not None:
        lines.append(f"* Leak scan of generated outputs (counts only): {out_scan}")
    if ann_status is not None:
        lines.append(f"* Annotation workbook: {ann_status.get('message')}")
    lines.append(f"* Issues: ERROR {rep.count('ERROR')}, WARN {rep.count('WARN')}, INFO {rep.count('INFO')}")
    lines.append("")
    for prof, r in runs.items():
        t = r["trace"]
        lines.append(f"* DISP-002 under {prof}: **{t.outcome}** (row {t.dt_row}), reasons {', '.join(t.reasons)}, "
                     f"flags {', '.join(t.flags)}, confidence {t.confidence['C']}, tier **{r['tier']['tier']}**")
    lines += ["", "## Issues", ""]
    lines.append(_tbl(["level", "check", "item", "message"], [(i.level, i.check, i.item, i.message) for i in rep.issues]) if rep.issues else "None.")
    lines += ["", "## Engine self-test (unit tests of the reference engine, not ground truth)", ""]
    lines.append(_tbl(["variant", "change", "outcome", "row", "tier", "C", "result"],
                      [(t["id"], t["variant"], t["got"]["outcome"], t["got"]["row"], t["got"]["tier"], t["got"]["C"],
                        "pass" if t["ok"] else "FAIL: " + "; ".join(t["problems"])) for t in tests]))
    lines += ["", "## Entity coverage (ONT.6)", ""]
    lines.append(_tbl(["entity", "name", "kind", "covered by", "status"],
                      [(x["entity"], x["name"], x["kind"], x["covered_by"], x["status"]) for x in rep.tables.get("entity_coverage", [])]))
    lines += ["", "## Rule sources and quote verification", ""]
    lines.append(_tbl(["rule", "#", "type", "doc", "doc date", "profile", "status", "where", "quote", "note"],
                      [(q["rule"], q["i"], q["type"], q["doc"], q["doc_date"], q["profile"], q["status"], q["where"], q["quote"][:110], q["note"][:90])
                       for q in rep.quotes]))
    lines += ["", "## Credibility review", ""]
    lines.append(_tbl(["rule", "type", "credibility", "mode", "weakest essential parameter", "source types", "note"],
                      [(c["rule"], c["type"], c["credibility"], c["mode"], c["weakest_param"], c["source_types"], c["note"][:120]) for c in rep.credibility]))
    return "\n".join(lines) + "\n"


def trace_report(kb, runs) -> str:
    lines = ["# DISP-002 evaluated with the knowledge base", "",
             "Reference evaluation without an LLM: the run-agreement (A) and rules-engine agreement (R) terms of the confidence score are set to 1.0.", ""]
    for prof, r in runs.items():
        t, tier, sens = r["trace"], r["tier"], r["sensitivity"]
        lines += [f"## Profile {prof}", ""]
        lines.append(_tbl(["playbook", "step", "rule", "status", "result", "evidence"],
                          [(s["playbook"], s["n"], s["rule"], s["status"], s["result"], ", ".join(s["evidence"])) for s in t.steps]))
        lines += ["", "Findings:", ""]
        lines.append(_tbl(["finding", "value", "unit", "status", "rule", "basis", "parameters"],
                          [(k, v["value"], v["unit"], v["status"], v["rule"], ", ".join(v["basis"]), ", ".join(v["params"]))
                           for k, v in t.findings.items() if not k.startswith("_")]))
        lines += ["", f"Outcome **{t.outcome}** via {t.dt_row}; reasons {t.reasons}; remedy {t.remedy}; flags {t.flags}", ""]
        if t.notes:
            lines += [f"Notes: {t.notes}", ""]
        lines += ["Sensitivity test (decisive definition, clause 2):", ""]
        lines.append(_tbl(["parameter", "value", "plausible range", "credibility", "at low end", "at high end", "decisive", "path rules using it"],
                          [(s["param"], s["value"], s["range"], s["credibility"], s["low"], s["high"],
                            "yes (outcome changes)" if s["outcome_changes"] else ("yes (lower-rated row)" if s["weaker_row"] else "no"),
                            ", ".join(s["rules_using"])) for s in sens]))
        lines += ["", "Reading test (decisive definition, clause 1):", ""]
        lines.append(_tbl(["rule", "reading", "other reading", "outcome under the other reading", "changes"],
                          [(x["rule"], x["reading"], x["other_reading"], x["outcome_other"], x["changes"]) for x in r["readings"]]) if r["readings"] else "None.")
        lines += ["", f"Confidence {t.confidence}", "",
                  f"Tier **{tier['tier']}**; decisive {tier['decisive']}; triggers {tier['triggers']}; gates {tier['gates']}; "
                  f"runtime-only gates not evaluated here: {tier['runtime_only_gates']}", ""]
        ex = explain.noshow(kb, r)
        lines += ["Explanation drafts (EXP-01 to EXP-03):", "", f"* Rider: {ex['rider']}", f"* Driver: {ex['driver']}",
                  f"* Numbers registered: {ex['numbers_used']}; unmatched numbers: {ex['exp03_unmatched'] or 'none'}", ""]
    return "\n".join(lines) + "\n"

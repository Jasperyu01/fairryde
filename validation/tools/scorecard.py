"""V5.1 (execution): compute the five pre-registered metrics, Wilson 95% intervals, threshold status and the decision.

Reads only the saved checkpoint files of the earlier primitives and 01_plan.yaml (thresholds and decision rule). Nothing here
is a judgment: verdicts come from the reviewers, the overlap adjudicator (V3.2) and the end-to-end adjudicator (V4.7).
Systematic issues are detected mechanically: two or more failing items in one layer that share a failure attribute
(the same credibility error, or the same implicated rule ID).

Output: V5_scorecard/51_scorecard.json, and a short table on stdout.
"""
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

V = Path(__file__).resolve().parent.parent
Z = 1.959964


def lines(rel):
    return [json.loads(l) for l in (V / rel).read_text(encoding="utf-8").splitlines() if l.strip()]


def wilson(k, n):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def parse(th):
    op, val = th.split()
    return op, float(val)


def status(rate, th, lower_is_better=False):
    for level in ("good", "acceptable"):
        op, val = parse(th[level])
        ok = rate >= val if op == ">=" else rate <= val
        if ok:
            return level.upper()
    return "BAD"


plan = yaml.safe_load((V / "01_plan.yaml").read_text())
TH = plan["thresholds"]
RID = re.compile(r"\b(?:CLS|CW|FC|DM|SE|EX|EXP|GEN|AUTH|FRD|MAT|DQ|META)-[A-Z]?\d+[A-Z]?\b")

# ---------------------------------------------------------------- V1 taxonomy
v1 = lines("V1_taxonomy/13_verdicts.jsonl")
kb_lab = {r["case_id"]: r for r in lines("V1_taxonomy/11_labels_kb.jsonl")}
blind = {r["case_id"]: r for r in lines("V1_taxonomy/12_labels_judge_blind.jsonl")}
n1 = len(v1)
pass1 = sum(r["verdict"] == "PASS" for r in v1)
uncovered = [r["case_id"] for r in v1 if r["verdict"] == "UNCOVERED"]
same_primary = sum(kb_lab[c]["primary_type"] == blind[c]["primary_type"] for c in kb_lab)
catch_all = {"NONE", "FC-OTHER", "SE-OTHER", "CW-OTHER", "DM-OTHER", "EX-OTHER"}
same_primary_catchall = sum(kb_lab[c]["primary_type"] == blind[c]["primary_type"] or
                            (kb_lab[c]["primary_type"] in catch_all and blind[c]["primary_type"] in catch_all) for c in kb_lab)
same_dispute = sum(kb_lab[c]["is_dispute"] == blind[c]["is_dispute"] for c in kb_lab)
routing_wrong = [r["case_id"] for r in v1 if r.get("is_dispute_ok") is False]
strict1 = sum(r["verdict"] == "PASS" and r.get("is_dispute_ok") is not False for r in v1)
def_mentions = Counter()
for r in v1:
    for code in set(re.findall(r"\b(?:CW|FC|DM|SE|EX)-[A-Z]+\b|\bCLS-\d+\b", r.get("definition_issue") or "")):
        def_mentions[code] += 1
M1 = {"name": "Taxonomy Accuracy", "num": pass1, "den": n1, "rate": round(pass1 / n1, 3), "wilson95": wilson(pass1, n1),
      "status": status(pass1 / n1, TH["M1_taxonomy_accuracy"]), "thresholds": TH["M1_taxonomy_accuracy"],
      "verdicts": dict(Counter(r["verdict"] for r in v1)),
      "supplementary": {
          "coverage": round(1 - len(uncovered) / n1, 3), "uncovered": uncovered,
          "blind_judge_vs_kb_same_primary": f"{same_primary}/{n1}",
          "same_primary_if_catch_all_equals_NONE": f"{same_primary_catchall}/{n1}",
          "blind_judge_vs_kb_same_is_dispute": f"{same_dispute}/{n1}",
          "is_dispute_wrong_after_review": routing_wrong,
          "strict_accuracy_type_and_routing": {"num": strict1, "den": n1, "rate": round(strict1 / n1, 3), "wilson95": wilson(strict1, n1)},
          "codes_most_named_in_definition_issues": def_mentions.most_common(6)}}

# ---------------------------------------------------------------- V2 ontology
v2 = lines("V2_ontology/21_verdicts.jsonl")
n2 = len(v2)
pass2 = sum(r["verdict"] == "PASS" for r in v2)
M2 = {"name": "Ontology Grounding Rate", "num": pass2, "den": n2, "rate": round(pass2 / n2, 3), "wilson95": wilson(pass2, n2),
      "status": status(pass2 / n2, TH["M2_ontology_grounding_rate"]), "thresholds": TH["M2_ontology_grounding_rate"],
      "verdicts": dict(Counter(r["verdict"] for r in v2)),
      "non_pass": [{"id": r["item_id"], "item": r["label"], "verdict": r["verdict"], "severity": r["severity"]} for r in v2 if r["verdict"] != "PASS"],
      "supplementary": {"pass_if_unsupported_minor_design_additions_were_allowed":
                        f"{pass2 + sum(r['verdict'] == 'UNSUPPORTED' and r['severity'] == 'MINOR' for r in v2)}/{n2}"}}

# ---------------------------------------------------------------- V3 rules
sample = json.loads((V / "V3_rules/30_sample.json").read_text())
final = {}
for tag in ("a", "b"):
    for r in lines(f"V3_rules/32_final_{tag}.jsonl"):
        final.setdefault(r["rule_id"], {})[tag] = r
adj = {r["rule_id"]: r for r in lines("V3_rules/33_overlap_adjudication.jsonl")}


def settled(rid):
    """Final verdict for one rule: the adjudicator's where both reviewers saw it, else the single reviewer's."""
    by = final[rid]
    # implicated rules: the reviewers' structured conflicts fields only (not free-text mentions)
    imp = {c.get("rule_id") for r in by.values() for c in (r.get("conflicts") or []) if c.get("rule_id")}
    if rid in adj:
        a = adj[rid]
        return {"verdict": a["final_verdict"], "severity": a["severity"], "credibility_check": a["credibility_check"],
                "credibility_label": next(iter(by.values())).get("credibility_label"),
                "source": "V3.2 adjudication", "reviewers": {t: by[t]["final_verdict"] for t in by},
                "reason": a["reason"], "implicated": sorted(imp - {rid})}
    (t, r), = by.items()
    return {"verdict": r["final_verdict"], "severity": r["severity"], "credibility_check": r.get("credibility_check"),
            "credibility_label": r.get("credibility_label"), "source": f"V3.1{t}", "reason": r.get("reason"),
            "implicated": sorted(imp - {rid})}


strata = {}
rules_rows = []
for s, ids in sample["sample"].items():
    pop = sample["strata"][s]["population"]
    ks = 0
    for rid in ids:
        f = settled(rid)
        ks += f["verdict"] == "PASS"
        rules_rows.append({"rule_id": rid, "stratum": s, **f})
    strata[s] = {"population": pop, "sample": len(ids), "pass": ks}
n3 = sum(v["sample"] for v in strata.values())
pass3 = sum(v["pass"] for v in strata.values())
N = sum(v["population"] for v in strata.values())
ps = sum(v["population"] / N * v["pass"] / v["sample"] for v in strata.values())
var = sum((v["population"] / N) ** 2 * (v["pass"] / v["sample"]) * (1 - v["pass"] / v["sample"]) / max(1, v["sample"] - 1)
          * (1 - v["sample"] / v["population"]) for v in strata.values())
crit = [settled(r) | {"rule_id": r} for r in sample["critical_path"]["row_rules"]]
M3 = {"name": "Rule Grounding Rate", "num": pass3, "den": n3, "rate": round(pass3 / n3, 3), "wilson95": wilson(pass3, n3),
      "status": status(pass3 / n3, TH["M3_rule_grounding_rate"]), "thresholds": TH["M3_rule_grounding_rate"],
      "verdicts": dict(Counter(r["verdict"] for r in rules_rows)),
      "by_credibility_stratum": {s: f"{v['pass']}/{v['sample']}" for s, v in strata.items()},
      "supplementary": {
          "post_stratified_kb_level_estimate": round(ps, 3),
          "post_stratified_status": status(ps, TH["M3_rule_grounding_rate"]),
          "post_stratified_approx_95": [round(ps - Z * math.sqrt(var), 3), round(ps + Z * math.sqrt(var), 3)],
          "approx_note": "normal approximation with finite-population correction; strata of 3 to 7 rules make it rough",
          "critical_path_DT_CW_NOSHOW_R8": [{"rule_id": c["rule_id"], "verdict": c["verdict"], "severity": c["severity"],
                                             "credibility_check": c["credibility_check"]} for c in crit],
          "credibility_checks_all_22_reviewed": dict(Counter(r["credibility_check"] for r in rules_rows + [c for c in crit if c["rule_id"] in sample["critical_path"]["not_drawn"]])),
          "credibility_too_high_among_B_and_C_reviewed": "{}/{}".format(
              sum(r["credibility_check"] == "TOO_HIGH" for r in rules_rows + [c for c in crit if c["rule_id"] in sample["critical_path"]["not_drawn"]] if r.get("credibility_label") in ("B", "C")),
              sum(1 for r in rules_rows + [c for c in crit if c["rule_id"] in sample["critical_path"]["not_drawn"]] if r.get("credibility_label") in ("B", "C")))}}

# ---------------------------------------------------------------- M4
fail4 = [("rule", r["rule_id"], r["verdict"], r["severity"]) for r in rules_rows if r["verdict"] in ("UNSUPPORTED", "CONFLICT")] + \
        [("ontology", r["item_id"], r["verdict"], r["severity"]) for r in v2 if r["verdict"] in ("UNSUPPORTED", "CONFLICT")]
n4 = n3 + n2
k4 = len(fail4)
k4_serious = sum(f[3] in ("CRITICAL", "MAJOR") for f in fail4)
M4 = {"name": "Conflict/Unsupported Rate", "num": k4, "den": n4, "rate": round(k4 / n4, 3), "wilson95": wilson(k4, n4),
      "status": status(k4 / n4, TH["M4_conflict_unsupported_rate"], lower_is_better=True), "thresholds": TH["M4_conflict_unsupported_rate"],
      "direction": "lower is better", "items": [{"layer": a, "id": b, "verdict": c, "severity": d} for a, b, c, d in fail4],
      "supplementary": {"critical_or_major_only": {"num": k4_serious, "den": n4, "rate": round(k4_serious / n4, 3),
                                                    "wilson95": wilson(k4_serious, n4),
                                                    "status": status(k4_serious / n4, TH["M4_conflict_unsupported_rate"], True)},
                        "overlap_note": "M4's numerator is a subset of the M2 and M3 failures, so M2, M3 and M4 are not independent signals"}}

# ---------------------------------------------------------------- V4 end to end
ref = {r["case_id"]: r for r in lines("V4_e2e/42_reference.jsonl")}
cmp_ = lines("V4_e2e/44_comparison.jsonl")
adj4 = {r["case_id"]: r for r in lines("V4_e2e/45_adjudication.jsonl")}
settled_cases = [c for c in cmp_ if ref[c["case_id"]]["settled"]]
n5 = len(settled_cases)
k5 = sum(c["verdict"] == "CORRECT" for c in settled_cases)
k5s = sum(c["strict_correct"] for c in settled_cases)
M5 = {"name": "Held-out Decision Accuracy", "num": k5, "den": n5, "rate": round(k5 / n5, 3), "wilson95": wilson(k5, n5),
      "status": status(k5 / n5, TH["M5_heldout_decision_accuracy"]), "thresholds": TH["M5_heldout_decision_accuracy"],
      "by_decider": {d: f"{sum(c['verdict'] == 'CORRECT' for c in settled_cases if c['route'] == d)}/{sum(c['route'] == d for c in settled_cases)}"
                     for d in ("engine", "kb_applier")},
      "errors": [{"case_id": c["case_id"], "reference": c["reference_outcome"], "kb": c["kb_outcome"], "kb_amount": c["kb_amount"],
                  "kb_tier": c["kb_tier"], "cause": adj4[c["case_id"]]["cause"], "severity": adj4[c["case_id"]]["severity"],
                  "direction": adj4[c["case_id"]]["direction"], "rules": adj4[c["case_id"]]["rule_ids_implicated"]}
                 for c in settled_cases if c["verdict"] != "CORRECT"],
      "supplementary": {"strict_accuracy_same_human_route": {"num": k5s, "den": n5, "rate": round(k5s / n5, 3), "wilson95": wilson(k5s, n5)},
                        "safety_cases_reaching_a_human": f"{sum(c['kb_tier'] == 'HUMAN' for c in settled_cases if c['case_id'] == 'E13')}/1",
                        "references_settled": f"{n5}/{len(ref)}",
                        "error_direction": dict(Counter(adj4[c["case_id"]]["direction"] for c in settled_cases if c["verdict"] != "CORRECT"))}}

metrics = {"M1": M1, "M2": M2, "M3": M3, "M4": M4, "M5": M5}

# ---------------------------------------------------------------- systematic issues (mechanical)
systematic = []
too_high = sorted({r["rule_id"] for r in rules_rows + crit if r.get("credibility_check") == "TOO_HIGH"})
if len(too_high) >= 2:
    sev = [r["severity"] for r in rules_rows + crit if r["rule_id"] in too_high and r["verdict"] != "PASS"]
    systematic.append({"layer": "rules", "pattern": "credibility label higher than the KB's own credibility_principle allows "
                       "(a Ryde condition extended by FairRyde should be D)", "members": too_high,
                       "critical": "CRITICAL" in sev})
imp_count = defaultdict(set)
for r in rules_rows + crit:
    if r["verdict"] != "PASS":
        for i in r["implicated"]:
            imp_count[i].add(r["rule_id"])
for i, members in sorted(imp_count.items()):
    if len(members) >= 2:
        sev = [r["severity"] for r in rules_rows + crit if r["rule_id"] in members]
        systematic.append({"layer": "rules", "pattern": f"failing rules that implicate the same rule {i}", "members": sorted(members),
                           "critical": "CRITICAL" in sev})
e2e_imp = defaultdict(set)
for c in M5["errors"]:
    for i in c["rules"]:
        e2e_imp[i].add(c["case_id"])
for i, members in sorted(e2e_imp.items()):
    if len(members) >= 2 and not i.startswith("DT-"):
        sev = [c["severity"] for c in M5["errors"] if c["case_id"] in members]
        systematic.append({"layer": "end_to_end", "pattern": f"end-to-end errors caused by the same rule {i}", "members": sorted(members),
                           "critical": "CRITICAL" in sev})
ont_unsup = [r["item_id"] for r in v2 if r["verdict"] == "UNSUPPORTED"]
if len(ont_unsup) >= 2:
    systematic.append({"layer": "ontology", "pattern": "design relations with no source and no design label", "members": ont_unsup,
                       "critical": any(r["severity"] == "CRITICAL" for r in v2 if r["item_id"] in ont_unsup)})
for code, cnt in def_mentions.items():
    if cnt >= 3:
        systematic.append({"layer": "taxonomy", "pattern": f"definition issue (not a verdict failure) naming {code} in {cnt} texts",
                           "members": [r["case_id"] for r in v1 if code in (r.get("definition_issue") or "")], "critical": False})
# the same failing items counted once: patterns in one layer with identical members are merged (e.g. CW-F06 and CW-R12 in E01, E03, E07)
merged = {}
for s in systematic:
    key = (s["layer"], tuple(s["members"]))
    if key in merged:
        merged[key]["pattern"] += " / " + s["pattern"].split(" ")[-1]
        merged[key]["critical"] = merged[key]["critical"] or s["critical"]
    else:
        merged[key] = dict(s)
systematic = list(merged.values())

# ---------------------------------------------------------------- decision (pre-registered rule)
n_bad = sum(m["status"] == "BAD" for m in metrics.values())
n_good = sum(m["status"] == "GOOD" for m in metrics.values())
cp_critical = [c["rule_id"] for c in crit if c["severity"] == "CRITICAL"]
sys_critical = [s for s in systematic if s["critical"]]
if n_bad == 0 and n_good >= 3 and not cp_critical and not systematic:
    verdict = "GO"
elif n_bad >= 2 or sys_critical:
    verdict = "NO_GO"
else:
    verdict = "CONDITIONAL_GO"


def lenient(m3_ps=False, m2_design=False, m4_serious=False):
    st = {k: m["status"] for k, m in metrics.items()}
    if m3_ps:
        st["M3"] = M3["supplementary"]["post_stratified_status"]
    if m2_design:
        k = int(M2["supplementary"]["pass_if_unsupported_minor_design_additions_were_allowed"].split("/")[0])
        st["M2"] = status(k / n2, TH["M2_ontology_grounding_rate"])
    if m4_serious:
        st["M4"] = M4["supplementary"]["critical_or_major_only"]["status"]
    bad = sum(v == "BAD" for v in st.values())
    return {"statuses": st, "bad": bad, "verdict": "NO_GO" if bad >= 2 or sys_critical else
            ("GO" if bad == 0 and sum(v == "GOOD" for v in st.values()) >= 3 and not cp_critical and not systematic else "CONDITIONAL_GO")}


expand = []
for k, m in metrics.items():
    lo, hi = m["wilson95"]
    bad_line = parse(m["thresholds"]["acceptable"])[1]
    if (k == "M4" and hi > bad_line) or (k != "M4" and lo < bad_line):
        expand.append(k)

ev = json.loads((V / "V5_scorecard/50_evidence_check.json").read_text())
out = {
    "kb_version": plan["meta"]["kb_version"],
    "plan_sha256": (V / "01_plan.sha256").read_text().split()[0],
    "metrics": metrics,
    "decision": {
        "verdict": verdict,
        "checks": {"metrics_bad": n_bad, "metrics_good": n_good,
                   "critical_findings_on_DISP002_path": cp_critical,
                   "systematic_issues": len(systematic), "systematic_critical": len(sys_critical)},
        "rule": plan["decision_rule"],
        "robustness": {"registered": lenient(),
                       "M3_post_stratified": lenient(m3_ps=True),
                       "M3_post_stratified_and_M2_design_allowed": lenient(m3_ps=True, m2_design=True),
                       "all_three_lenient_readings": lenient(True, True, True)},
        "expand_next_round": {"layers": expand, "rule": plan["decision_rule"]["expand"]}},
    "systematic_issues": systematic,
    "rules_detail": rules_rows,
    "critical_path_detail": crit,
    "evidence_traceability": {"quotes_checked": sum(ev["total"].values()), "verified_in_cited_file": ev["total"]["VERIFIED"],
                              "found_in_another_source_file": ev["total"]["FOUND_ELSEWHERE"], "not_found": ev["total"]["NOT_FOUND"],
                              "share": ev["verified_share"]},
}
(V / "V5_scorecard/51_scorecard.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))

print(f"{'metric':38} {'value':>12} {'Wilson 95%':>16}  status")
for k, m in metrics.items():
    print(f"{k} {m['name']:35} {m['num']:>3}/{m['den']:<3}={m['rate']:.3f} [{m['wilson95'][0]:.3f}, {m['wilson95'][1]:.3f}]  {m['status']}")
print("M3 post-stratified:", M3["supplementary"]["post_stratified_kb_level_estimate"], M3["supplementary"]["post_stratified_approx_95"],
      M3["supplementary"]["post_stratified_status"], "| by stratum", M3["by_credibility_stratum"])
print("critical path:", [(c["rule_id"], c["verdict"], c["severity"], c["credibility_check"]) for c in crit])
print("systematic:")
for s in systematic:
    print("  ", s["layer"], "|", s["pattern"], "|", s["members"], "| CRITICAL" if s["critical"] else "")
print("DECISION:", verdict, out["decision"]["checks"])
for k, v in out["decision"]["robustness"].items():
    print("  robustness", k, v["verdict"], v["statuses"])
print("expand next round:", expand)
print("evidence:", out["evidence_traceability"])

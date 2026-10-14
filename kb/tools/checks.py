"""Integrity checks for the FairRyde knowledge base.

Each check appends Issue(level, check, item, message). Levels: ERROR (must fix), WARN (review), INFO.
The checks follow the ChordX protocol: sources and credibility for every rule (ONT.4 Step 5), layer dependencies
(ONT.2), OTHER values in business vocabularies (ONT.4 Step 4), the real sample mapped completely (ONT.1),
and decision tables that are complete and unique.
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field

from kbload import KB, A_CUTOFF, collect_values, expand_rule_refs, leaf_paths, norm

LEVELS = ("ERROR", "WARN", "INFO")
RULE_ID_RE = re.compile(r"\b[A-Z]{2,4}-[A-Z]?\d+[A-Z]?\b")


@dataclass
class Issue:
    level: str
    check: str
    item: str
    message: str


@dataclass
class Report:
    issues: list = field(default_factory=list)
    quotes: list = field(default_factory=list)        # one row per rule source
    credibility: list = field(default_factory=list)   # one row per rule
    tables: dict = field(default_factory=dict)

    def add(self, level, check, item, message):
        self.issues.append(Issue(level, check, item, message))

    def count(self, level):
        return sum(1 for i in self.issues if i.level == level)


# ---------------------------------------------------------------------------------------------- helpers
def _known_conflict_sides(kb: KB) -> set:
    """(doc, normalized quote) for every side of a META-04 known conflict (clause level)."""
    sides = set()
    for r in kb.y["rules"]["rules"]:
        for c in r.get("known_conflicts", []) or []:
            if isinstance(c, dict):
                for sd in c.get("sides", []):
                    sides.add((sd["doc"], norm(sd["quote"])))
    return sides


def _is_conflict_side(src: dict, sides: set) -> bool:
    return bool(src.get("quote")) and (src.get("doc"), norm(src["quote"])) in sides


def _qualifies(src: dict, kb: KB, level: str, sides: set = frozenset()) -> bool:
    t = src.get("type")
    if level == "A":
        if _is_conflict_side(src, sides):
            return False            # credibility_principle: a clause on one side of a known conflict never counts toward A
        if t in ("ORGANIZER", "RYDE_TOU", "INTERNAL_STANDARD"):
            return True
        if t == "RYDE_POLICY":
            d = kb.sources.get(src.get("doc"), {})
            return d.get("date", "") >= A_CUTOFF
        return False
    if level == "B":
        return t in ("ORGANIZER", "RYDE_TOU", "RYDE_POLICY", "REGULATION", "GOV_GUIDANCE", "INTERNAL_STANDARD")
    if level == "C":
        return t in ("ORGANIZER", "RYDE_TOU", "RYDE_POLICY", "REGULATION", "GOV_GUIDANCE", "INTERNAL_STANDARD", "INDUSTRY")
    return True


def _rule_refs_in(text) -> list[str]:
    return expand_rule_refs(text) if text else []


# ---------------------------------------------------------------------------------------------- checks
def check_ids(kb: KB, rep: Report):
    seen = {}
    for r in kb.y["rules"]["rules"]:
        if r["id"] in seen:
            rep.add("ERROR", "unique-ids", r["id"], "duplicate rule id")
        seen[r["id"]] = True
    for v in kb.y["taxonomy"]["vocabularies"]:
        codes = []

        def walk(vals):
            for x in vals:
                codes.append(str(x["code"]))
                walk(x.get("children", []))
        walk(v["values"])
        dups = {c for c in codes if codes.count(c) > 1}
        for d in dups:
            rep.add("ERROR", "unique-ids", f"{v['id']}:{d}", "duplicate code in vocabulary")
    for kind, items in (("entity", kb.y["ontology"]["entities"]), ("playbook", kb.y["playbooks"]["playbooks"]),
                        ("source", kb.y["sources"]["documents"])):
        ids = [i["id"] for i in items]
        for d in {i for i in ids if ids.count(i) > 1}:
            rep.add("ERROR", "unique-ids", d, f"duplicate {kind} id")


def check_taxonomy(kb: KB, rep: Report):
    tax = kb.y["taxonomy"]
    scopes = set(tax["scope_values"])
    for vid, meta in kb.vocab_meta.items():
        codes = list(kb.vocab[vid])
        has_other = any(c.upper() == "OTHER" or c.upper().endswith("-OTHER") for c in codes)
        if not has_other and not meta.get("closed"):
            rep.add("ERROR", "taxonomy-other", vid, "business vocabulary without an OTHER value (ONT.4 Step 4)")
        if meta.get("closed") and not meta.get("closed_reason"):
            rep.add("WARN", "taxonomy-other", vid, "closed vocabulary without closed_reason")
    for code, x in kb.case_leaves.items():
        if x.get("scope") not in scopes:
            rep.add("ERROR", "taxonomy-scope", code, f"scope {x.get('scope')!r} not in scope_values")
        pb = x.get("playbook") or tax.get("scope_playbooks", {}).get(x.get("scope"))
        if x.get("scope") in ("ADJUDICATE", "ADJUDICATE_WITH_APPROVAL", "TRIAGE_TO_HUMAN", "ROUTE_TO_SUPPORT", "BACKLOG"):
            if not pb:
                rep.add("ERROR", "taxonomy-playbook", code, "no playbook (directly or by scope)")
            elif pb not in kb.playbooks:
                rep.add("ERROR", "taxonomy-playbook", code, f"playbook {pb} does not exist")
        if not x.get("label"):
            rep.add("ERROR", "taxonomy-fields", code, "missing label")
    # term sources: Ryde article ids and titles or quoted body text; organizer quotes (handbook, DISP-002)
    bad = 0
    checked = 0
    hb, _ = kb.source_text("ORG-HANDBOOK")
    dp, _ = kb.source_text("ORG-DISP002")
    qre = re.compile(r"'([^']*(?:'[a-z][^']*)*)'")

    def tnorm(x):
        return re.sub(r"\s+([?.!,])", r"\1", norm(x).lower())
    for vid, entries in kb.vocab.items():
        for code, x in entries.items():
            texts = list(x.get("term_sources", []) or [])
            if x.get("term_source"):
                texts.append(x["term_source"])
            parts = [pt for tx in texts for pt in str(tx).split("; ")]
            for t in parts:
                item = f"{vid}:{code}"
                ids = list(re.finditer(r"\b(\d{9,})\b", t))
                for k, m in enumerate(ids):
                    aid = m.group(1)
                    seg = t[m.end(): ids[k + 1].start() if k + 1 < len(ids) else len(t)]
                    a = kb.articles.get(aid)
                    if not a:
                        if not _is_section(kb, aid):
                            bad += 1
                            rep.add("ERROR", "taxonomy-terms", item, f"id {aid} is neither a captured article nor a section")
                        continue
                    for q in qre.findall(seg):
                        checked += 1
                        if tnorm(q) != tnorm(a["title"]) and tnorm(q) not in tnorm(a["title"] + " " + a["body_text"]):
                            bad += 1
                            rep.add("ERROR", "taxonomy-terms", item, f"'{q[:60]}' is neither the title nor in the body of article {aid} ('{a['title']}')")
                if not ids and ("Handbook" in t or "DISP-002" in t):
                    for q in qre.findall(t):
                        checked += 1
                        if norm(q) not in hb and norm(q) not in dp:
                            bad += 1
                            rep.add("ERROR", "taxonomy-terms", item, f"organizer quote not found: '{q[:60]}'")
    rep.tables["term_sources_checked"] = checked
    rep.tables["term_sources_bad"] = bad


def _is_section(kb: KB, sid: str) -> bool:
    sl = kb.corpus.get("section_listings", {})
    blob = str(sl)
    return sid in blob


def check_rules(kb: KB, rep: Report):
    rmeta = kb.y["rules"]
    types = set(rmeta["types"])
    modes = set(rmeta["modes"])
    src_types = set(kb.vocab["TX-SOURCE-TYPE"])
    reasons = set(kb.vocab["TX-REASON"])
    case_codes = set(kb.vocab["TX-CASE"])
    sides = _known_conflict_sides(kb)
    for r in kb.y["rules"]["rules"]:
        for c in r.get("known_conflicts", []) or []:
            if not isinstance(c, dict) or len(c.get("sides", [])) < 2:
                rep.add("ERROR", "conflicts", r["id"], "known conflict needs a topic and at least two sides with doc and quote")
                continue
            for sd in c["sides"]:
                text, _ = kb.source_text(sd["doc"])
                if text is None or norm(sd["quote"]) not in text:
                    rep.add("ERROR", "conflicts", r["id"], f"conflict side not found verbatim in {sd['doc']}: {sd['quote'][:70]}")
    required = ["id", "name", "family", "type", "applies_to", "statement", "zh", "sources", "credibility", "mode", "status"]
    produced = {}
    for r in kb.y["rules"]["rules"]:
        rid = r["id"]
        for f in required:
            if f not in r or r[f] in (None, ""):
                rep.add("ERROR", "rule-fields", rid, f"missing field {f}")
        if r.get("type") not in types:
            rep.add("ERROR", "rule-fields", rid, f"type {r.get('type')!r} not in types")
        if r.get("mode") not in modes:
            rep.add("ERROR", "rule-fields", rid, f"mode {r.get('mode')!r} not in modes")
        if r.get("credibility") not in ("A", "B", "C", "D"):
            rep.add("ERROR", "rule-fields", rid, "credibility must be A, B, C or D")
        for a in r.get("applies_to", []) or []:
            if a != "ALL" and a not in case_codes:
                rep.add("ERROR", "rule-applies", rid, f"applies_to {a} is not a TX-CASE code")
        for p in r.get("params", []) or []:
            if not kb.param_exists(p):
                rep.add("ERROR", "rule-params", rid, f"parameter {p} not in reference_data")
        for p in r.get("flag_only_params", []) or []:
            if p not in (r.get("params") or []):
                rep.add("ERROR", "rule-params", rid, f"flag_only_params {p} not listed in params")
        for c in r.get("produces", []) or []:
            produced.setdefault(c, []).append(rid)
            if c not in reasons:
                rep.add("ERROR", "rule-reasons", rid, f"produces {c}, which is not in TX-REASON")
        pfs = r.get("produces_finding") or []
        pfs = pfs if isinstance(pfs, list) else [pfs]
        for pf in pfs:
            if pf not in kb.findings:
                rep.add("ERROR", "rule-findings", rid, f"produces_finding {pf} not in ontology finding_types")
            else:
                pb_ = kb.findings[pf].get("produced_by")
                if rid not in (pb_ if isinstance(pb_, list) else [pb_]):
                    rep.add("ERROR", "rule-findings", rid, f"finding {pf} lists produced_by {pb_}")
        if r.get("type") == "outcome" and not r.get("produces"):
            rep.add("WARN", "rule-reasons", rid, "outcome rule produces no reason code")
        if r.get("decision_table") and r["decision_table"] not in rmeta.get("decision_tables", {}):
            rep.add("ERROR", "rule-dt", rid, f"decision table {r['decision_table']} not found")

        # sources and quotes
        srcs = r.get("sources", []) or []
        if not srcs:
            rep.add("ERROR", "rule-sources", rid, "no source")
        for i, s in enumerate(srcs):
            row = {"rule": rid, "i": i + 1, "type": s.get("type"), "doc": s.get("doc"), "clause": s.get("clause", ""),
                   "profile": s.get("profile", ""), "quote": s.get("quote", ""), "quote_kind": s.get("quote_kind", "verbatim"),
                   "status": "", "where": "", "doc_date": "", "note": s.get("note", "")}
            if s.get("type") not in src_types:
                rep.add("ERROR", "rule-sources", rid, f"source type {s.get('type')!r} not in TX-SOURCE-TYPE")
            doc = s.get("doc")
            d = kb.sources.get(doc)
            if not d:
                rep.add("ERROR", "rule-sources", rid, f"source document {doc} not registered")
                row["status"] = "UNKNOWN_DOC"
                rep.quotes.append(row)
                continue
            row["doc_date"] = d.get("date", "")
            if d.get("type") and s.get("type") and d["type"] != s["type"] and not (doc.startswith("RYDE-") and s["type"] == "RYDE_POLICY"):
                rep.add("WARN", "rule-sources", rid, f"source type {s['type']} differs from registry type {d['type']} for {doc}")
            if "quote" in s:
                text, where = kb.source_text(doc)
                q = norm(s["quote"])
                if text is None:
                    row["status"] = "NO_LOCAL_COPY"
                    rep.add("ERROR", "rule-quotes", rid, f"quote given but {doc} has no local copy to verify against")
                elif q in text:
                    row["status"] = "VERIFIED"
                    row["where"] = where
                else:
                    ks = kb.article_key_statements(doc)
                    if ks and q in ks:
                        row["status"] = "KEY_STATEMENT_ONLY"
                        row["where"] = "corpus key_statements"
                        rep.add("WARN", "rule-quotes", rid, f"quote found only in key_statements of {doc}: {s['quote'][:70]}")
                    else:
                        row["status"] = "NOT_FOUND"
                        rep.add("ERROR", "rule-quotes", rid, f"quote not found in {doc}: {s['quote'][:90]}")
                if doc == "RYDE-TOU" and row["status"] == "VERIFIED":
                    c = kb.tou_clause_for(s["quote"])
                    row["where"] = c["ref"] if c else row["where"]
                    if c and "excerpt" in c.get("status", ""):
                        rep.add("WARN", "rule-quotes", rid, f"ToU clause captured only as an excerpt: {c['ref']}")
                    m = re.search(r"s\.(\d+(?:\.\d+)?)", s.get("clause", ""))
                    if c and m:
                        num = m.group(1)
                        ok = (f" {num} " in c["ref"] + " ") or c["ref"].startswith(f"Section A, {num}.") or f"{num} " in c["ref"]
                        if not ok:
                            rep.add("WARN", "rule-quotes", rid, f"clause label {s['clause']!r} vs captured ref {c['ref']!r}")
            else:
                kind = s.get("quote_kind")
                if kind not in ("none", "paraphrase"):
                    rep.add("ERROR", "rule-quotes", rid, "source without quote must set quote_kind none or paraphrase")
                row["status"] = "PARAPHRASE" if kind == "paraphrase" else "NO_QUOTE (design assumption)"
                if s.get("type") in ("RYDE_POLICY", "RYDE_TOU", "ORGANIZER"):
                    rep.add("WARN", "rule-quotes", rid, f"{s.get('type')} source cited without a verbatim quote")
            if _is_conflict_side(s, sides):
                row["note"] = (row["note"] + " " if row["note"] else "") + "[clause is one side of a META-04 known conflict: does not count toward A]"
            rep.quotes.append(row)

        # credibility
        cred = r.get("credibility")
        profiles = sorted({s.get("profile") for s in srcs if s.get("profile")})
        if cred in ("A", "B", "C"):
            if profiles:
                for prof in profiles:
                    ok = any(_qualifies(s, kb, cred, sides) for s in srcs if s.get("profile") in (None, "", prof))
                    if not ok:
                        rep.add("ERROR", "rule-credibility", rid, f"rated {cred} but no {cred}-qualifying source for profile {prof}")
            elif not any(_qualifies(s, kb, cred, sides) for s in srcs):
                rep.add("ERROR", "rule-credibility", rid, f"rated {cred} but no {cred}-qualifying source")
        weakest = None
        order = {"A": 0, "B": 1, "C": 2, "D": 3}
        essential = [p for p in (r.get("params") or []) if p not in (r.get("flag_only_params") or [])]
        param_creds = {}
        for p in essential:
            for prof in kb.profiles:
                e = kb.param(p, prof)
                if e and e.get("credibility"):
                    param_creds[p] = max(param_creds.get(p, "A"), e["credibility"], key=lambda c: order[c])
        if param_creds:
            weakest = max(param_creds.values(), key=lambda c: order[c])
        if weakest and order[weakest] > order.get(cred, 0):
            rep.add("INFO" if r.get("credibility_note") else "WARN", "rule-credibility", rid,
                    f"rated {cred} but essential parameter(s) are {weakest}: "
                    + ", ".join(f"{p}={c}" for p, c in param_creds.items() if order[c] > order[cred])
                    + ("" if r.get("credibility_note") else " (add a credibility_note)"))
        rep.credibility.append({"rule": rid, "family": r.get("family"), "type": r.get("type"), "credibility": cred,
                                "mode": r.get("mode"), "weakest_param": weakest or "",
                                "source_types": ", ".join(sorted({s.get('type') for s in srcs})),
                                "note": r.get("credibility_note", "")})

    # decision table reason codes count as produced
    for dt_id, dt in rmeta.get("decision_tables", {}).items():
        for row in dt["rows"]:
            produced.setdefault(row["reason"], []).append(f"{dt_id}:{row['row']}")
    for c in reasons:
        if c not in produced:
            rep.add("ERROR", "reason-coverage", c, "TX-REASON code is produced by no rule or decision-table row")
    rep.tables["reason_producers"] = produced

    # TX-REASON outcome field must be a TX-OUTCOME code
    outcomes = set(kb.vocab["TX-OUTCOME"])
    for c, x in kb.vocab["TX-REASON"].items():
        if x.get("outcome") not in outcomes:
            rep.add("INFO", "reason-outcome", c, f"outcome field is descriptive: {x.get('outcome')!r}")

    # every finding type produced by its rule
    for code, f in kb.findings.items():
        pbs = f.get("produced_by")
        for pb in (pbs if isinstance(pbs, list) else [pbs]):
            if pb not in kb.rules:
                rep.add("ERROR", "finding-producer", code, f"produced_by {pb} is not a rule")
                continue
            decl = kb.rules[pb].get("produces_finding") or []
            if code not in (decl if isinstance(decl, list) else [decl]):
                rep.add("ERROR", "finding-producer", code, f"rule {pb} does not declare produces_finding {code}")


def check_decision_tables(kb: KB, rep: Report):
    rmeta = kb.y["rules"]
    outcomes = set(kb.vocab["TX-OUTCOME"])
    order = {"A": 0, "B": 1, "C": 2, "D": 3}
    flags = set(kb.vocab["TX-FLAG"])
    reasons = set(kb.vocab["TX-REASON"])
    summary = {}
    for dt_id, dt in rmeta.get("decision_tables", {}).items():
        inputs = dt["inputs"]
        names = list(inputs)
        for n in names:
            src = dt.get("input_sources", {}).get(n)
            if not src:
                rep.add("WARN", "dt-inputs", dt_id, f"input {n} has no input_sources entry")
                continue
            m = re.search(r"\((F-[A-Z\-]+)", str(src))
            fv = kb.findings.get(m.group(1), {}).get("values") if m else None
            if isinstance(fv, list) and [str(x) for x in fv] != [str(x) for x in inputs[n]]:
                rep.add("ERROR", "dt-inputs", f"{dt_id}.{n}", f"input values {inputs[n]} differ from finding {m.group(1)} values {fv}")
        if not dt.get("precondition"):
            rep.add("WARN", "dt-inputs", dt_id, "no precondition stated")
        for row in dt["rows"]:
            for k in row["when"]:
                if k not in inputs:
                    rep.add("ERROR", "dt-rows", f"{dt_id}:{row['row']}", f"condition on unknown input {k}")
            if row["outcome"] not in outcomes:
                rep.add("ERROR", "dt-rows", f"{dt_id}:{row['row']}", f"outcome {row['outcome']} not in TX-OUTCOME")
            if row["reason"] not in reasons:
                rep.add("ERROR", "dt-rows", f"{dt_id}:{row['row']}", f"reason {row['reason']} not in TX-REASON")
            rc = row.get("credibility")
            if rc not in order:
                rep.add("ERROR", "dt-credibility", f"{dt_id}:{row['row']}", "row needs credibility A, B, C or D")
            else:
                weakest = max((kb.rules[x]["credibility"] for x in row.get("rules", []) if x in kb.rules), key=lambda c: order[c], default="A")
                if rc != weakest:
                    rep.add("ERROR", "dt-credibility", f"{dt_id}:{row['row']}", f"rated {rc}, but the weakest rule it depends on is {weakest}")
            for f in row.get("flags", []) or []:
                if f not in flags:
                    rep.add("ERROR", "dt-rows", f"{dt_id}:{row['row']}", f"flag {f} not in TX-FLAG")
            for rid in (row.get("rules", []) or []) + (row.get("also", []) or []):
                if rid not in kb.rules:
                    rep.add("ERROR", "dt-rows", f"{dt_id}:{row['row']}", f"rule {rid} does not exist")
            prods = [rid for rid in row.get("rules", []) if row["reason"] in (kb.rules.get(rid, {}).get("produces") or [])]
            if not prods:
                rep.add("ERROR", "dt-rows", f"{dt_id}:{row['row']}", f"no rule in 'rules' produces the reason {row['reason']}")
        # enumeration: every combination hits exactly one row (hit policy UNIQUE)
        combos = list(itertools.product(*[inputs[n] for n in names]))
        gaps, overlaps = [], []
        hits_per_row = {row["row"]: 0 for row in dt["rows"]}
        for combo in combos:
            env = dict(zip(names, combo))
            hit = [row["row"] for row in dt["rows"] if _row_matches(row["when"], env)]
            for h in hit:
                hits_per_row[h] += 1
            if not hit:
                gaps.append(env)
            elif len(hit) > 1:
                overlaps.append((env, hit))
        if gaps:
            rep.add("ERROR", "dt-complete", dt_id, f"{len(gaps)} input combinations hit no row, first: {gaps[0]}")
        if overlaps:
            rep.add("ERROR", "dt-unique", dt_id, f"{len(overlaps)} combinations hit several rows, first: {overlaps[0]}")
        for r_id, n in hits_per_row.items():
            if n == 0:
                rep.add("ERROR", "dt-unique", f"{dt_id}:{r_id}", "row can never be hit")
        summary[dt_id] = {"combinations": len(combos), "gaps": len(gaps), "overlaps": len(overlaps), "hits_per_row": hits_per_row}
    rep.tables["decision_tables"] = summary


def _row_matches(when: dict, env: dict) -> bool:
    for k, v in when.items():
        allowed = v if isinstance(v, list) else [v]
        if env[k] not in allowed:
            return False
    return True


def check_playbooks(kb: KB, rep: Report):
    pmeta = kb.y["playbooks"]["meta"]
    modes = set(pmeta.get("answer_modes", {}))
    prims = set(pmeta["step_primitives"])
    for pb in kb.y["playbooks"]["playbooks"]:
        pid = pb["id"]
        for f in ("name", "display_name_zh", "when", "answer_mode", "status", "sources", "required_evidence", "steps"):
            if f not in pb:
                rep.add("ERROR", "playbook-fields", pid, f"missing {f}")
        if pb.get("answer_mode") not in modes:
            rep.add("ERROR", "playbook-fields", pid, f"answer_mode {pb.get('answer_mode')} not defined")
        tx = pb.get("when", {}).get("taxonomy")
        if tx and tx not in kb.vocab["TX-CASE"]:
            rep.add("ERROR", "playbook-when", pid, f"taxonomy {tx} does not exist")
        for s in pb.get("sources", []):
            if s not in kb.sources:
                rep.add("ERROR", "playbook-sources", pid, f"source {s} not registered")
        for st in pb.get("steps", []):
            if st["do"] not in prims:
                rep.add("ERROR", "playbook-steps", f"{pid}#{st['n']}", f"unknown primitive {st['do']}")
            for rid in _rule_refs_in(st.get("rule")):
                if rid not in kb.rules:
                    rep.add("ERROR", "playbook-steps", f"{pid}#{st['n']}", f"rule {rid} does not exist")
            if st.get("table") and st["table"] not in kb.y["rules"].get("decision_tables", {}):
                rep.add("ERROR", "playbook-steps", f"{pid}#{st['n']}", f"table {st['table']} does not exist")
            if st["do"] in ("COMPUTE", "CHECK", "DECIDE", "READ") and not (st.get("rule") or st.get("table")):
                rep.add("WARN", "playbook-steps", f"{pid}#{st['n']}", f"{st['do']} step names no rule or table")
            if st["do"] == "READ":
                for rid in _rule_refs_in(st.get("rule")):
                    if rid in kb.rules and kb.rules[rid]["mode"] == "HARD":
                        rep.add("WARN", "playbook-steps", f"{pid}#{st['n']}", f"READ step on HARD rule {rid}")
    # every rule used by at least one playbook (or meta/auth rules which are global)
    used = set()
    for pb in kb.y["playbooks"]["playbooks"]:
        for st in pb.get("steps", []):
            used.update(_rule_refs_in(st.get("rule")))
    dt_rules = set()
    for dt in kb.y["rules"].get("decision_tables", {}).values():
        for row in dt["rows"]:
            dt_rules.update(row.get("rules", []))
            dt_rules.update(row.get("also", []) or [])
    unused = [rid for rid in kb.rule_order if rid not in used and rid not in dt_rules
              and kb.rules[rid]["family"] not in ("META", "AUTH", "EXP")]
    for rid in unused:
        rep.add("WARN", "playbook-coverage", rid, "rule is not used by any playbook step or decision table")
    rep.tables["rules_not_in_playbooks"] = unused


def check_ontology(kb: KB, rep: Report):
    ont = kb.y["ontology"]
    vocabs = set(kb.vocab)
    roles = set(kb.vocab["TX-ROLE"])
    for e in ont["entities"]:
        for a in e.get("attributes", []) or []:
            t = str(a.get("type", ""))
            for v in re.findall(r"TX-[A-Z\-]+[A-Z]", t):
                if v not in vocabs:
                    rep.add("ERROR", "ontology-types", f"{e['id']}.{a['name']}", f"vocabulary {v} does not exist")
            for ref in re.findall(r"ENT-[A-Z]+", t):
                if ref not in kb.entities:
                    rep.add("ERROR", "ontology-types", f"{e['id']}.{a['name']}", f"entity {ref} does not exist")
            for sm in re.findall(r"SM-[A-Z]+", t):
                if sm not in kb.state_machines:
                    rep.add("ERROR", "ontology-types", f"{e['id']}.{a['name']}", f"state machine {sm} does not exist")
    # events <-> TX-EVENT (ONT.2: ontology event types converge into the taxonomy's controlled list)
    ev_codes = {e["code"] for e in ont["events"]}
    tx_events = {c for c in kb.vocab["TX-EVENT"] if c != "other"}
    for c in sorted(tx_events - ev_codes):
        rep.add("ERROR", "event-convergence", c, "TX-EVENT value has no ontology event (actor, target, state change)")
    for c in sorted(ev_codes - tx_events):
        rep.add("ERROR", "event-convergence", c, "ontology event missing from TX-EVENT")
    role_tokens = roles | {"CLAIMANT", "RESPONDENT", "PAYEE", "PAYER", "REVIEWER", "PLATFORM"}
    for e in ont["events"]:
        for tok in re.findall(r"\b[A-Z_]{4,}\b", f"{e.get('actor','')} {e.get('target','')}"):
            if tok not in role_tokens:
                rep.add("WARN", "event-roles", e["code"], f"actor/target token {tok} is not a TX-ROLE")
        for sm, frm, to in re.findall(r"(SM-[A-Z]+): ([A-Z_\-\*]+|any pre-pickup state) -> ([A-Z_]+)", e.get("changes", "")):
            states = kb.state_machines.get(sm)
            if states is None:
                rep.add("ERROR", "event-states", e["code"], f"state machine {sm} does not exist")
                continue
            for st in (frm, to):
                if st in ("-",) or "*" in st or st.startswith("any"):
                    continue
                if st not in states:
                    rep.add("ERROR", "event-states", e["code"], f"state {st} not in {sm}")
    for r in ont["roles"]:
        for ent in re.findall(r"ENT-[A-Z]+", str(r.get("played_by", "")) + " " + str(r.get("in", ""))):
            if ent not in kb.entities:
                rep.add("ERROR", "ontology-roles", r["code"], f"entity {ent} does not exist")
        if r["code"] not in roles:     # ONT.2: ontology roles converge into the taxonomy's role list
            rep.add("ERROR", "role-convergence", r["code"], "ontology role missing from TX-ROLE")
    ont_roles = {r["code"] for r in ont["roles"]}
    for c in sorted(roles - ont_roles - {"OTHER", "PLATFORM"}):
        rep.add("WARN", "role-convergence", c, "TX-ROLE value has no ontology role (who plays it, in what)")
    check_states(kb, rep)
    for rel in ont["relations"]:
        for ent in re.findall(r"ENT-[A-Z]+", f"{rel['subject']} {rel['object']}"):
            if ent not in kb.entities:
                rep.add("ERROR", "ontology-relations", f"{rel['subject']} {rel['predicate']}", f"entity {ent} does not exist")


PRE_PICKUP = ["REQUESTED", "MATCHED", "EN_ROUTE", "ARRIVED", "WAITING_FREE", "WAITING_CHARGEABLE"]


def check_states(kb: KB, rep: Report):
    """Every state is reachable from a creating event; dead ends are exactly the declared terminal states."""
    ont = kb.y["ontology"]
    sms = ont["state_machines"]
    trans = {sm: set() for sm in sms}
    for e in ont["events"]:
        for part in str(e.get("changes", "")).split(";"):
            m = re.match(r"\s*(SM-[A-Z]+): (.+?) -> ([A-Z_]+)", part)
            if not m or m.group(1) not in sms:
                continue
            sm, frm, to = m.groups()
            if frm == "-":
                frms = ["-"]
            elif frm.endswith("*"):
                frms = [x for x in sms[sm] if x.startswith(frm[:-1])]
            elif frm.startswith("any pre-pickup"):
                frms = PRE_PICKUP
            else:
                frms = [frm]
            for f in frms:
                trans[sm].add((f, to))
    summary = {}
    for sm, states in sms.items():
        reach, frontier = set(), [to for f, to in trans[sm] if f == "-"]
        while frontier:
            x = frontier.pop()
            if x in reach:
                continue
            reach.add(x)
            frontier.extend(to for f, to in trans[sm] if f == x)
        for st in states:
            if st not in reach:
                rep.add("ERROR", "state-reachability", f"{sm}:{st}", "state cannot be reached from any creating event")
        dead = {st for st in states if not any(f == st and to != st for f, to in trans[sm])}
        declared = set((ont.get("terminal_states") or {}).get(sm, []) or [])
        for st in sorted(dead - declared):
            rep.add("ERROR", "state-terminal", f"{sm}:{st}", "no event leaves this state, but it is not declared terminal")
        for st in sorted(declared - dead):
            rep.add("ERROR", "state-terminal", f"{sm}:{st}", "declared terminal, but an event leaves it")
        summary[sm] = {"states": len(states), "reachable": len(reach & set(states)), "terminal": sorted(declared)}
    rep.tables["state_machines"] = summary


def check_disp002_mapping(kb: KB, rep: Report):
    ont = kb.y["ontology"]
    data = kb.disp002
    leaves = leaf_paths(data)
    mapped = {m["path"]: m for m in ont["disp002_mapping"]}
    rows = []
    for p in leaves:
        if p not in mapped:
            rep.add("ERROR", "disp002-mapping", p, "DISP-002 field not mapped to the ontology")
    for p, m in mapped.items():
        vals = leaves.get(p)
        status = "ok"
        if vals is None:
            rep.add("ERROR", "disp002-mapping", p, "mapping path does not exist in DISP-002")
            status = "missing path"
            vals = []
        # entity.attribute targets
        for ent_name, attr in re.findall(r"\b([A-Z][A-Za-z]+)\.([a-z_]+)\b", str(m["maps_to"])):
            e = kb.entity_by_name.get(ent_name)
            if e is None:
                continue
            names = {a["name"] for a in e.get("attributes", []) or []}
            if attr not in names:
                rep.add("ERROR", "disp002-mapping", p, f"{ent_name}.{attr} is not an attribute of {e['id']}")
                status = "bad target"
        vocab = m.get("vocab")
        resolved = []
        if vocab:
            vid = vocab.split()[0]
            for v in vals:
                code = kb.resolve(vid, v)
                resolved.append(f"{v} -> {code}")
                if code is None:
                    rep.add("ERROR", "disp002-vocab", p, f"value {v!r} does not resolve in {vid}")
                    status = "unresolved value"
        if m.get("param"):
            prof = kb.y["reference_data"]["profiles"]["organizer_case"]
            expected = (prof.get("case_example_DISP002", {}).get(m["param"]) or {}).get("value")
            got = vals[0] if vals else None
            if m["param"] not in prof.get("case_fields", {}):
                rep.add("ERROR", "disp002-params", p, f"{m['param']} is mapped from the policy object but is not a case_field of organizer_case")
            if m["param"] == "FEE_PAYEE":
                ok = (got == "driver_compensation" and expected == "DRIVER")
            else:
                ok = got is not None and expected is not None and abs(float(got) * float(m.get("scale", 1)) - float(expected)) < 1e-9
            if not ok:
                rep.add("ERROR", "disp002-params", p, f"value {got} x {m.get('scale', 1)} != case_example_DISP002.{m['param']} = {expected}")
                status = "param mismatch"
            resolved.append(f"{got} -> {m['param']} = {expected} (read from each case)")
        sample = vals[0] if vals else ""
        rows.append({"path": p, "maps_to": m["maps_to"], "vocab": vocab or "", "sample": sample,
                     "n_values": len(vals), "resolved": "; ".join(dict.fromkeys(resolved)), "status": status,
                     "note": m.get("note", "")})
    rep.tables["disp002_mapping"] = rows
    rep.tables["disp002_leaf_count"] = len(leaves)


def check_case_mapping(kb: KB, rep: Report, case_id: str, key: str):
    """The same completeness check as for DISP-002, for the two samples uploaded on 14 Oct 2026: every leaf field of the case file is
    mapped, every entity.attribute target exists, and a mapped vocabulary resolves every value."""
    ont = kb.y["ontology"]
    data = kb.organizer_cases[case_id]
    leaves = leaf_paths(data)
    mapped = {m["path"]: m for m in ont[key]}
    rows = []
    tag = key.replace("_mapping", "-mapping")
    for p in leaves:
        if p not in mapped:
            rep.add("ERROR", tag, p, f"{case_id} field not mapped to the ontology")
    for p, m in mapped.items():
        vals = leaves.get(p)
        status = "ok"
        if vals is None:
            rep.add("ERROR", tag, p, f"mapping path does not exist in {case_id}")
            status, vals = "missing path", []
        for ent_name, attr in re.findall(r"\b([A-Z][A-Za-z]+)\.([a-z_]+)\b", str(m["maps_to"])):
            e = kb.entity_by_name.get(ent_name)
            if e is None:
                rep.add("ERROR", tag, p, f"{ent_name} is not an entity of the ontology")
                status = "bad target"
                continue
            if attr not in {a["name"] for a in e.get("attributes", []) or []}:
                rep.add("ERROR", tag, p, f"{ent_name}.{attr} is not an attribute of {e['id']}")
                status = "bad target"
        vocab = m.get("vocab")
        resolved = []
        if vocab:
            vid = vocab.split()[0]
            for v in vals:
                code = kb.resolve(vid, v)
                resolved.append(f"{v} -> {code}")
                if code is None:
                    rep.add("ERROR", tag.replace("mapping", "vocab"), p, f"value {v!r} does not resolve in {vid}")
                    status = "unresolved value"
        rows.append({"path": p, "maps_to": m["maps_to"], "vocab": vocab or "", "sample": vals[0] if vals else "", "n_values": len(vals),
                     "resolved": "; ".join(dict.fromkeys(resolved)), "status": status, "note": m.get("note", "")})
    rep.tables[key] = rows
    rep.tables[key + "_leaf_count"] = len(leaves)


def check_annotation(kb: KB, rep: Report, evidence_ids: set = frozenset()):
    """The example row belongs to the made-up case EXAMPLE-01, so evidence examples are checked against the ID pattern."""
    ann = kb.y["annotation_schema"]
    fill_modes = set(ann["fill_modes"])
    ev_re = re.compile(kb.entities["ENT-EVIDENCE"]["id_regex"])
    names = [c["name"] for g in ann["groups"].values() for c in g["columns"]]
    for d in {n for n in names if names.count(n) > 1}:
        rep.add("ERROR", "annotation-cols", d, "duplicate column name")
    dt_rows = [r["row"] for r in kb.y["rules"]["decision_tables"]["DT-CW-NOSHOW"]["rows"]] + ["n/a"]
    for g in ann["groups"].values():
        for c in g["columns"]:
            if c["name"] == "decision_table_row" and [str(x) for x in c.get("values", [])] != dt_rows:
                rep.add("ERROR", "annotation-cols", "decision_table_row", f"values {c.get('values')} differ from the decision table rows {dt_rows}")
            if c["name"] == "autonomy_tier" and c.get("vocab") != "TX-TIER-AUTONOMY":
                rep.add("ERROR", "annotation-cols", "autonomy_tier", "must use TX-TIER-AUTONOMY")
    ex_case = next((c.get("example") for g in ann["groups"].values() for c in g["columns"] if c["name"] == "case_id"), "")
    if str(ex_case).upper().startswith("DISP-"):
        rep.add("ERROR", "annotation-example", "case_id", "the example row must be a made-up case, not an organizer case (no model-drafted answers for real cases)")
    blind = [c["name"] for g in ann["groups"].values() for c in g["columns"] if c.get("hide_in_blind")]
    inp = [c["name"] for c in ann["groups"]["INPUT"]["columns"]]
    if blind and inp[-len(blind):] != blind:
        rep.add("WARN", "annotation-cols", "hide_in_blind", "hide_in_blind columns should be contiguous at the end of INPUT so they can be grouped and hidden")
    groups_required = {"INPUT", "ANSWER", "BASIS", "RELATION"}
    if not groups_required <= set(ann["groups"]):
        rep.add("ERROR", "annotation-groups", "groups", f"missing column groups {groups_required - set(ann['groups'])} (ONT.5)")
    for g, grp in ann["groups"].items():
        for col in grp["columns"]:
            name = f"{g}.{col['name']}"
            if col.get("fill") not in fill_modes:
                rep.add("ERROR", "annotation-cols", name, f"fill {col.get('fill')} not defined")
            if g in ("ANSWER", "BASIS") and col.get("fill") != "HUMAN":
                rep.add("ERROR", "annotation-cols", name, "answer and basis columns must be HUMAN (ONT.5: never pre-filled by the system under test)")
            vocab = str(col.get("vocab", "")).split(" ")[0] if col.get("vocab") else None
            ex = col.get("example")
            if vocab and vocab.startswith("TX-"):
                if vocab not in kb.vocab:
                    rep.add("ERROR", "annotation-cols", name, f"vocabulary {vocab} does not exist")
                elif ex not in (None, ""):
                    for v in str(ex).split("; "):
                        if kb.resolve(vocab, v) is None:
                            rep.add("ERROR", "annotation-example", name, f"example {v!r} not in {vocab}")
            if col.get("vocab") == "rule ids" and ex:
                for v in str(ex).split("; "):
                    if v not in kb.rules:
                        rep.add("ERROR", "annotation-example", name, f"example rule {v} does not exist")
            if col.get("vocab") == "source ids" and ex:
                for v in str(ex).split("; "):
                    if v not in kb.sources:
                        rep.add("ERROR", "annotation-example", name, f"example source {v} does not exist")
            if col.get("vocab") == "evidence ids" and ex:
                for v in str(ex).split("; "):
                    if not ev_re.match(v):
                        rep.add("ERROR", "annotation-example", name, f"example evidence {v} does not match the evidence id pattern")
            if col.get("values") and ex not in (None, "") and str(ex) not in [str(x) for x in col["values"]]:
                rep.add("ERROR", "annotation-example", name, f"example {ex!r} not in values {col['values']}")


def check_entity_coverage(kb: KB, rep: Report, cases: dict):
    """ONT.6: every business entity type appears in at least one case file. Case-processing entities are created by the pipeline."""
    ont = kb.y["ontology"]
    rows = []
    for e in ont["entities"]:
        row = {"entity": e["id"], "name": e["name"], "kind": e.get("kind", ""), "covered_by": "", "status": ""}
        maps = {"DISP-001": ont["disp001_mapping"], "DISP-003": ont["disp003_mapping"]}
        cov = []
        for cid, c in cases.items():
            paths = [m["path"] for m in maps.get(cid, ont["disp002_mapping"]) if re.search(r"\b" + re.escape(e["name"]) + r"\b", str(m["maps_to"]))]
            if any(v not in (None, "", []) for p in paths for v in collect_values(c, p)):
                cov.append(cid)
        if e.get("present_in_every_case"):
            row["covered_by"], row["status"] = "every case", "ok"
        elif cov:
            row["covered_by"], row["status"] = ", ".join(cov), "ok (from the case file)"
        elif e["id"] == "ENT-REVIEW":
            row["status"] = "created when a person reviews a ruling (APPROVE and HUMAN tiers)"
        elif e["id"] == "ENT-PRECEDENT":
            row["status"] = "created only from human-reviewed rulings"
        elif e.get("kind") not in ("business", "value_object"):
            row["status"] = "created by the pipeline for every case"
        else:
            row["status"] = "not covered by any case file yet"
            rep.add("INFO", "entity-coverage", e["id"], "no case file exercises this entity yet (ONT.6); include one when building the case set")
        rows.append(row)
    rep.tables["entity_coverage"] = rows


def check_inventory(kb: KB, rep: Report):
    allowed = ("PUBLIC", "INTERNAL", "PII", "CONFIDENTIAL")
    for it in kb.y["inventory"]["items"]:
        for f in ("item", "provider", "format", "layer", "sensitivity", "status", "if_missing"):
            if f not in it:
                rep.add("ERROR", "inventory", it.get("item", "?"), f"missing column {f} (ONT.3)")
        if not str(it.get("sensitivity", "")).startswith(allowed):
            rep.add("WARN", "inventory", it["item"][:50], f"sensitivity {it.get('sensitivity')!r} not in {allowed}")


def check_reference_data(kb: KB, rep: Report):
    for name, e in list(kb.shared.items()) + [(f"{p}.{k}", v) for p, params in kb.profiles.items() for k, v in params.items()]:
        if "credibility" not in e:
            rep.add("ERROR", "reference-data", name, "missing credibility")
        if "retrieved" not in e:
            rep.add("WARN", "reference-data", name, "missing retrieved date (ONT.10b: value, source, date, note)")
        if e.get("credibility") in ("C", "D") and isinstance(e.get("value"), (int, float)) and "plausible_range" not in e:
            rep.add("WARN", "reference-data", name, "C/D numeric parameter without plausible_range (needed for the AUTH-02 sensitivity test)")
        pr = e.get("plausible_range")
        if pr and isinstance(e.get("value"), (int, float)) and not (pr[0] <= e["value"] <= pr[1]):
            rep.add("ERROR", "reference-data", name, f"value {e['value']} outside its plausible_range {pr}")
    for name, t in kb.tables.items():
        for f in ("source", "credibility", "retrieved"):
            if f not in t:
                rep.add("WARN", "reference-data", name, f"table missing {f}")


def check_scope(kb: KB, rep: Report):
    sc = kb.y["scope"]
    for key in ("adjudicate", "adjudicate_with_approval", "triage_to_human", "route_to_support"):
        for code in sc["scope_v0_1"][key]:
            if code not in kb.case_leaves:
                rep.add("ERROR", "scope", code, f"{key} lists a code that is not a TX-CASE leaf")
    expect = {"adjudicate": "ADJUDICATE", "adjudicate_with_approval": "ADJUDICATE_WITH_APPROVAL",
              "triage_to_human": "TRIAGE_TO_HUMAN", "route_to_support": "ROUTE_TO_SUPPORT"}
    for key, scope in expect.items():
        listed = set(sc["scope_v0_1"][key])
        actual = {c for c, x in kb.case_leaves.items() if x.get("scope") == scope}
        if listed != actual:
            rep.add("ERROR", "scope", key, f"scope.yaml lists {sorted(listed)} but taxonomy has {sorted(actual)}")
    text, _ = kb.source_text("ORG-HANDBOOK")
    for tr in sc["decision_goal"]["track_requirements"]:
        if norm(tr["quote"]) not in text:
            rep.add("ERROR", "scope", tr["quote"][:50], "handbook quote not found")
    for cq in sc["competency_questions"]:
        for rid in RULE_ID_RE.findall(cq["answered_by"]):
            if rid not in kb.rules and rid not in kb.y["rules"].get("decision_tables", {}):
                rep.add("ERROR", "scope", cq["q"][:40], f"answered_by names unknown rule {rid}")


def check_text_style(kb: KB, rep: Report):
    """No em or en dashes in our own files (team writing rule); quotes were normalized."""
    import glob
    import os
    for f in sorted(glob.glob(str(kb.dir / "*.yaml"))):
        s = open(f, encoding="utf-8").read()
        for ch, nm in (("–", "en dash"), ("—", "em dash")):
            if ch in s:
                rep.add("WARN", "style", os.path.basename(f), f"contains {s.count(ch)} {nm}(es)")


def run_all(kb: KB, evidence_ids: set = frozenset(), cases: dict | None = None) -> Report:
    rep = Report()
    check_ids(kb, rep)
    check_taxonomy(kb, rep)
    check_rules(kb, rep)
    check_decision_tables(kb, rep)
    check_playbooks(kb, rep)
    check_ontology(kb, rep)
    check_disp002_mapping(kb, rep)
    check_case_mapping(kb, rep, "DISP-001", "disp001_mapping")
    check_case_mapping(kb, rep, "DISP-003", "disp003_mapping")
    check_annotation(kb, rep, evidence_ids)
    check_entity_coverage(kb, rep, cases or {"DISP-001": kb.disp001, "DISP-002": kb.disp002, "DISP-003": kb.disp003})
    check_inventory(kb, rep)
    check_reference_data(kb, rep)
    check_scope(kb, rep)
    check_text_style(kb, rep)
    return rep

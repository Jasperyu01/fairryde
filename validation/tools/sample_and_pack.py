"""P2: draw the seeded stratified samples (plan 01_plan.yaml) and build the packets each reviewer is allowed to see.

Outputs (all under validation/):
  V3_rules/30_sample.json            sampled rule IDs by stratum, plus the critical-path set
  V2_ontology/20_sample.json         sampled ontology items by stratum
  packs/sources/<doc>.txt            full text of every document cited by a sampled rule (and the ontology sources)
  packs/rules/<id>.pass1.json        rule without credibility, builder notes or FairRyde source entries
  packs/rules/<id>.pass2.json        the hidden fields, opened only after the pass-1 verdict is written
  packs/ontology/<n>.json            one ontology item with its declared source and context
  packs/taxonomy/taxonomy_packet.json  dispute types, roles and the classification rules
  packs/policy/                      Ryde articles, Terms of Use, handbook, DISP-002 (for the case writer and labeler)
  packs/kb/                          KB YAML files (for the KB applier)
"""
import json
import random
import shutil
import sys
from pathlib import Path

import yaml

KB = Path("/home/claude/work/kb")
V = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KB / "tools"))
from kbload import KB as K  # noqa: E402

plan = yaml.safe_load((V / "01_plan.yaml").read_text())
SEED = plan["sampling"]["seed"]
kb = K(KB)
corpus = kb.corpus


def doc_text(doc_id: str) -> str:
    """Full text of a cited document, with its registry metadata on top."""
    meta = kb.sources.get(doc_id, {})
    head = f"DOCUMENT {doc_id}\nTITLE: {meta.get('title', '')}\nTYPE: {meta.get('type', '')}\nURL: {meta.get('url', '')}\nDATE: {meta.get('date', '')}\n"
    if doc_id.startswith("RYDE-") and doc_id != "RYDE-TOU":
        a = kb.articles.get(doc_id[5:])
        if not a:
            return head + "\n(no local copy)\n"
        return head + f"AUDIENCE: {a['audience']}\nSECTION: {a.get('section_name')}\nEDITED: {a['edited_at'][:10]}\n\n{a['title']}\n\n{a['body_text']}\n"
    if doc_id == "RYDE-TOU":
        tou = corpus["terms_of_use"]
        return head + "\n\n".join(f"[{c['ref']}] ({c.get('topic', '')})\n{c['text']}" for c in tou["clauses"]) + "\n"
    if doc_id == "FAIRRYDE-DECISIONS":
        return head + "FairRyde's own design-decision log (open_items.yaml):\n\n" + (KB / "open_items.yaml").read_text(encoding="utf-8")
    va = meta.get("verify_against")
    if va and not va.startswith("corpus#") and "#" not in va and (KB / va).exists():
        return head + f"LOCAL COPY: kb/{va}\n\n" + (KB / va).read_text(encoding="utf-8")
    return head + "\n(no local copy of this document)\n"


def write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        path.write_text(obj, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str), encoding="utf-8")


# ------------------------------------------------------------------ rules (V3)
rng = random.Random(f"{SEED}-rules")
strata = plan["sampling"]["rules"]["strata_by_credibility"]
by_cred = {c: sorted(r for r, x in kb.rules.items() if x["credibility"] == c) for c in strata}
for c, s in strata.items():
    assert len(by_cred[c]) == s["population"], (c, len(by_cred[c]), s["population"])
sample = {c: sorted(rng.sample(by_cred[c], s["sample"])) for c, s in strata.items()}
drawn = {r for ids in sample.values() for r in ids}
r8 = next(x for x in kb.y["rules"]["decision_tables"]["DT-CW-NOSHOW"]["rows"] if x["row"] == "R8")
critical = [r for r in r8["rules"] if r not in drawn]
write(V / "V3_rules/30_sample.json", {"seed": f"{SEED}-rules", "strata": strata, "sample": sample,
                                      "critical_path": {"source": "DT-CW-NOSHOW row R8 rules (decided DISP-002)", "row_rules": r8["rules"], "not_drawn": critical}})

HIDE = ("credibility", "credibility_note", "status", "open_question", "note", "notes", "conflict_note")
docs_needed = set()
for rid in sorted(drawn) + critical:
    r = kb.rules[rid]
    p1_sources, hidden_sources = [], []
    for s in r.get("sources", []):
        if s["type"] == "FAIRRYDE":
            hidden_sources.append(s)
            continue
        docs_needed.add(s["doc"])
        p1_sources.append({k: v for k, v in s.items() if k not in ("note",)} | {"source_file": f"packs/sources/{s['doc']}.txt"})
        if s.get("note"):
            hidden_sources.append({"doc": s["doc"], "note": s["note"]})
    params = []
    for name in r.get("params") or []:
        e = kb.param(name, "ryde_2026") or kb.param(name, "organizer_case") or {}
        params.append({"name": name, "value": e.get("value"), "unit": e.get("unit")})
    pass1 = {"rule_id": rid, "name": r["name"], "family": r["family"], "type": r["type"], "applies_to": r.get("applies_to"),
             "mode": r.get("mode"), "statement": r["statement"], "params": params, "produces": r.get("produces"),
             "produces_finding": r.get("produces_finding"), "sources": p1_sources,
             "set": "critical_path" if rid in critical else "random"}
    pass2 = {"rule_id": rid, **{k: r.get(k) for k in HIDE if r.get(k) is not None}, "fairryde_sources_and_source_notes": hidden_sources}
    write(V / f"packs/rules/{rid}.pass1.json", pass1)
    write(V / f"packs/rules/{rid}.pass2.json", pass2)

# ------------------------------------------------------------------ ontology (V2)
o = kb.y["ontology"]
rng_o = random.Random(f"{SEED}-ontology")
pools = {
    "entity_business": [e for e in o["entities"] if e.get("kind") == "business"],
    "entity_case": [e for e in o["entities"] if e.get("kind") == "case"],
    "role": o["roles"],
    "relation": o["relations"],
    "event": o["events"],
}
ont_sample = {}
n = 0
for stratum, k in plan["sampling"]["ontology"]["strata"].items():
    pool = pools[stratum]
    picks = rng_o.sample(range(len(pool)), k)
    ont_sample[stratum] = []
    for idx in sorted(picks):
        n += 1
        item = pool[idx]
        iid = f"O{n:02d}"
        ctx = {}
        if stratum == "event":
            sm = item.get("changes", "").split(":")[0].strip()
            ctx["state_machine"] = {sm: o["state_machines"].get(sm)} if sm in o["state_machines"] else None
        if stratum == "relation":
            for side in ("subject", "object"):
                for code in str(item.get(side, "")).replace(" ", "").split("|"):
                    if code in kb.entities:
                        ctx.setdefault("entity_definitions", {})[code] = {k2: kb.entities[code].get(k2) for k2 in ("name", "kind", "definition", "source")}
        if stratum == "role":
            ctx["role_notes"] = o.get("role_notes")
        write(V / f"packs/ontology/{iid}.json", {"item_id": iid, "stratum": stratum, "item": item, "context": ctx,
                                                  "source_files": ["packs/sources/ORG-DISP002.txt", "packs/sources/RYDE-TOU.txt",
                                                                   "packs/sources/ORG-HANDBOOK.txt", "packs/policy/ryde_articles/ (index: packs/policy/ryde_articles_index.tsv)"]})
        ont_sample[stratum].append({"item_id": iid, "index_in_pool": idx, "label": item.get("id") or item.get("code") or f"{item.get('subject')} {item.get('predicate')} {item.get('object')}"})
write(V / "V2_ontology/20_sample.json", {"seed": f"{SEED}-ontology", "strata": plan["sampling"]["ontology"]["strata"], "sample": ont_sample})
docs_needed |= {"ORG-DISP002", "RYDE-TOU", "ORG-HANDBOOK"}

for d in sorted(docs_needed):
    write(V / f"packs/sources/{d}.txt", doc_text(d))

# ------------------------------------------------------------------ taxonomy packet (V1)
def leaves(vals, parent=None):
    out = []
    for x in vals:
        item = {k: x.get(k) for k in ("code", "level", "label", "definition", "excludes", "example_phrases", "scope", "term_note") if x.get(k) is not None}
        item["category"] = parent
        out.append(item)
        if "children" in x:
            out += leaves(x["children"], x["code"])
    return out


tx_case = next(v for v in kb.y["taxonomy"]["vocabularies"] if v["id"] == "TX-CASE")
tx_role = next(v for v in kb.y["taxonomy"]["vocabularies"] if v["id"] == "TX-ROLE")
write(V / "packs/taxonomy/taxonomy_packet.json", {
    "note": "Classify each complaint with these dispute types. Scope says what FairRyde does with a type; it does not change the type.",
    "TX-CASE": {"assigned_when": tx_case.get("assigned_when"), "values": leaves(tx_case["values"])},
    "TX-ROLE (who files)": [{k: x.get(k) for k in ("code", "label")} for x in tx_role["values"]],
    "classification_rules": {rid: {"name": kb.rules[rid]["name"], "statement": kb.rules[rid]["statement"]} for rid in sorted(kb.rules) if rid.startswith("CLS-")},
})

# ------------------------------------------------------------------ policy pack (V4 writer and labeler) and KB pack (V4 applier)
pol = V / "packs/policy"
idx_lines = ["id\ttitle\taudience\tsection\tedited"]
for aid, a in sorted(kb.articles.items()):
    write(pol / f"ryde_articles/{aid}.txt", f"RYDE HELP CENTRE ARTICLE {aid}\nTITLE: {a['title']}\nAUDIENCE: {a['audience']}\nSECTION: {a.get('section_name')}\n"
                                             f"URL: {a['url']}\nEDITED: {a['edited_at'][:10]}\n\n{a['body_text']}\n")
    idx_lines.append(f"{aid}\t{a['title']}\t{a['audience']}\t{a.get('section_name')}\t{a['edited_at'][:10]}")
write(pol / "ryde_articles_index.tsv", "\n".join(idx_lines) + "\n")
write(pol / "ryde_terms_of_use.txt", doc_text("RYDE-TOU"))
write(pol / "organizer_handbook.txt", (KB / "sources/organizer/handbook.txt").read_text(encoding="utf-8"))
write(pol / "organizer_sample_DISP-002.md", (KB / "sources/organizer/disp002.md").read_text(encoding="utf-8"))
shutil.copytree(pol / "ryde_articles", V / "packs/policy_articles_check", dirs_exist_ok=True) if False else None

kbp = V / "packs/kb"
kbp.mkdir(parents=True, exist_ok=True)
for f in ("taxonomy.yaml", "ontology.yaml", "rules.yaml", "reference_data.yaml", "playbooks.yaml"):
    shutil.copy(KB / f, kbp / f)

print(json.dumps({"rules_sample": sample, "critical_path_extra": critical, "ontology_sample": {k: [x["label"] for x in v] for k, v in ont_sample.items()},
                  "source_docs": len(docs_needed), "policy_articles": len(kb.articles)}, indent=1, ensure_ascii=False))

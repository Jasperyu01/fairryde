"""V5.0: check mechanically that every evidence quote a reviewer gave exists in the file it cites.

A quote counts as VERIFIED if, after normalization (Unicode NFKC, straight quotes, hyphens for dashes, single spaces), it is a
substring of the cited file (raw text, or the string values of a JSON file). Quotes with "..." or "[...]" are split and every
part must be found. If the cited file does not contain it but another file in the packs does, it counts as FOUND_ELSEWHERE;
otherwise NOT_FOUND. Output: V5_scorecard/50_evidence_check.json with per-file counts and every non-verified quote.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

V = Path(__file__).resolve().parent.parent


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s))
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), (" ", " ")):
        s = s.replace(a, b)
    for ch in "–—−‐‑":
        s = s.replace(ch, "-")
    s = s.replace('\\"', '"')
    return re.sub(r"\s+", " ", s).strip().lower()


_cache = {}


def text_of(path: Path) -> str:
    if path in _cache:
        return _cache[path]
    raw = path.read_text(encoding="utf-8", errors="replace")
    parts = [raw]
    strings = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                strings.append(str(k))
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif o is not None:
            strings.append(str(o))
    try:
        if path.suffix == ".json":
            walk(json.loads(raw))
        elif path.suffix == ".jsonl":
            for line in raw.splitlines():
                if line.strip():
                    walk(json.loads(line))
        elif path.suffix == ".md" and "```json" in raw:
            walk(json.loads(re.search(r"```json\n(.*?)\n```", raw, re.S).group(1)))
    except Exception:
        pass
    parts.append("\n".join(strings))
    _cache[path] = norm("\n".join(parts))
    return _cache[path]


ALL_FILES = [p for p in (V / "packs").rglob("*") if p.is_file()] + [p for p in (V / "V4_e2e/cases").glob("*.json")] + \
            [V / "V1_taxonomy/10_cases_for_classifier.jsonl", V / "V1_taxonomy/10_cases.jsonl"]   # sources only, never reviewer outputs


def resolve(file_field, article_id=None):
    cands = []
    if file_field:
        f = str(file_field).strip()
        m = re.match(r"^(?:.*/)?(E\d\d)(?:\.json)?(?:\.|$|\s)", f)
        if m and (V / f"V4_e2e/cases/{m.group(1)}.json").exists():
            return V / f"V4_e2e/cases/{m.group(1)}.json"
        p = Path(f)
        for c in (p, V / f, V / "V1_taxonomy" / f, V / "V4_e2e" / f, V / "V4_e2e/cases" / f, V / "packs" / f):
            if c.is_file():
                return c
        base = p.name
        cands = [q for q in ALL_FILES if q.name == base]
        if cands:
            return cands[0]
        m = re.search(r"(\d{9,})", f)
        if m and (V / f"packs/policy/ryde_articles/{m.group(1)}.txt").exists():
            return V / f"packs/policy/ryde_articles/{m.group(1)}.txt"
    if article_id:
        a = str(article_id)
        m = re.search(r"(\d{9,})", a)
        if m and (V / f"packs/policy/ryde_articles/{m.group(1)}.txt").exists():
            return V / f"packs/policy/ryde_articles/{m.group(1)}.txt"
        if re.search(r"tou|terms|section|s\.\s*\d|clause", a, re.I):
            return V / "packs/policy/ryde_terms_of_use.txt"
        if "DISP" in a.upper():
            return V / "packs/policy/organizer_sample_DISP-002.md"
        if "handbook" in a.lower():
            return V / "packs/policy/organizer_handbook.txt"
    return None


def check(quote, file_field=None, article_id=None):
    q = str(quote or "").strip()
    if not q:
        return "EMPTY", None
    parts = [norm(x) for x in re.split(r"\s*(?:\[\.\.\.\]|\.\.\.|…|\s\|\s)\s*", q) if norm(x)]   # "..." and " | " separate fragments

    def squash(s):
        return re.sub(r"\s+", "", s)

    def found(t):
        ts = squash(t)
        return all(p in t or squash(p) in ts for p in parts)
    path = resolve(file_field, article_id)
    if path is not None and found(text_of(path)):
        return "VERIFIED", str(path.relative_to(V)) if str(path).startswith(str(V)) else str(path)
    for other in ALL_FILES:
        try:
            if found(text_of(other)):
                return "FOUND_ELSEWHERE", str(other.relative_to(V))
        except Exception:
            continue
    return "NOT_FOUND", str(path) if path else None


def items():
    """Yield (step, record id, quote, file, article_id) for every evidence quote in the reviewer outputs."""
    def lines(rel):
        p = V / rel
        if not p.exists():
            return []
        return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in lines("V2_ontology/21_verdicts.jsonl"):
        for e in r.get("evidence") or []:
            yield "V2.1", r["item_id"], e.get("quote"), e.get("file"), None
    for tag in ("a", "b"):
        for r in lines(f"V3_rules/32_pass1_{tag}.jsonl"):
            for el in r.get("elements") or []:
                for e in el.get("evidence") or []:
                    yield f"V3.1{tag}", r["rule_id"], e.get("quote"), e.get("file"), None
    for r in lines("V3_rules/33_overlap_adjudication.jsonl"):
        for e in r.get("evidence") or []:
            yield "V3.2", r["rule_id"], e.get("quote"), e.get("file"), None
    for r in lines("V1_taxonomy/11_labels_kb.jsonl"):
        yield "V1.2", r["case_id"], r.get("evidence"), "10_cases_for_classifier.jsonl", None
    for r in lines("V1_taxonomy/13_verdicts.jsonl"):
        for e in r.get("evidence") or []:
            yield "V1.3", r["case_id"], e.get("quote"), e.get("file"), None
    for rel, step in (("V4_e2e/40_intended.jsonl", "V4.1"), ("V4_e2e/41_labels_policy.jsonl", "V4.2")):
        for r in lines(rel):
            for b in r.get("basis") or []:
                yield step, r["case_id"], b.get("quote"), None, b.get("article_id")
    for r in lines("V4_e2e/45_adjudication.jsonl"):
        for e in r.get("evidence") or []:
            yield "V4.7", r["case_id"], e.get("quote"), e.get("file"), None


if __name__ == "__main__":
    res = {"by_step": {}, "problems": []}
    for step, rid, quote, f, aid in items():
        status, where = check(quote, f, aid)
        s = res["by_step"].setdefault(step, {"VERIFIED": 0, "FOUND_ELSEWHERE": 0, "NOT_FOUND": 0, "EMPTY": 0})
        s[status] += 1
        if status not in ("VERIFIED",):
            res["problems"].append({"step": step, "id": rid, "status": status, "cited": f or aid, "found_in": where, "quote": str(quote)[:200]})
    tot = {k: sum(s[k] for s in res["by_step"].values()) for k in ("VERIFIED", "FOUND_ELSEWHERE", "NOT_FOUND", "EMPTY")}
    res["total"] = tot
    res["verified_share"] = round((tot["VERIFIED"] + tot["FOUND_ELSEWHERE"]) / max(1, sum(tot.values())), 4)
    out = V / "V5_scorecard/50_evidence_check.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps({"by_step": res["by_step"], "total": tot, "verified_share": res["verified_share"]}, indent=1))
    for p in res["problems"][:30]:
        print(p)

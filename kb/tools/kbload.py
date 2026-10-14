"""Load the FairRyde knowledge base (YAML source of truth) and the bundled source documents.

Everything needed to verify the knowledge base lives under kb/, so the checks can be rerun on any machine:
    python3 build_kb.py
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import yaml

KB_DIR = Path(__file__).resolve().parent.parent
TODAY = "2026-10-05"
A_CUTOFF = "2025-10-05"          # Ryde articles edited on or after this date are "within 12 months"

YAML_FILES = ["taxonomy", "ontology", "rules", "reference_data", "playbooks", "sources",
              "inventory", "annotation_schema", "scope", "privacy", "open_items", "protocol_gap", "precedents", "organizer_cases"]

ORGANIZER_FILES = {"DISP-001": "disp001.md", "DISP-002": "disp002.md", "DISP-003": "disp003.md"}     # sources/organizer/
ORGANIZER_PROFILE = "organizer_v2_1"          # the default profile of an organizer case (rule META-01, decision D41)


def is_organizer_case(case: dict) -> bool:
    """An organizer case carries the organizer's own dispute id (DISP-nnn); the regression and synthetic cases do not."""
    return bool(re.fullmatch(r"DISP-\d+", str((case.get("dispute_ticket") or {}).get("dispute_id", ""))))


def default_profile(case: dict) -> str:
    """META-01: organizer_v2_1 for an organizer case; organizer_case (legacy) for another case that embeds a policy object; else ryde_2026."""
    if is_organizer_case(case):
        return ORGANIZER_PROFILE
    return "organizer_case" if case.get("cancellation_policy") else "ryde_2026"


def norm(text: str) -> str:
    """Normalize text for verbatim comparison: Unicode NFKC, straight quotes, hyphens for dashes, single spaces."""
    s = unicodedata.normalize("NFKC", str(text))
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), (" ", " ")):
        s = s.replace(a, b)
    for ch in "–—−‐‑":
        s = s.replace(ch, "-")
    return re.sub(r"\s+", " ", s).strip()


class KB:
    def __init__(self, kb_dir: Path = KB_DIR):
        self.dir = Path(kb_dir)
        self.y = {}
        for name in YAML_FILES:
            with open(self.dir / f"{name}.yaml", encoding="utf-8") as fh:
                self.y[name] = yaml.safe_load(fh)
        with open(self.dir / "sources/ryde_policy_corpus.json", encoding="utf-8") as fh:
            self.corpus = json.load(fh)
        md = (self.dir / "sources/organizer/disp002.md").read_text(encoding="utf-8")
        self.disp002_md = md
        self.disp002 = json.loads(re.search(r"```json\n(.*?)\n```", md, re.S).group(1))
        self.organizer_cases = {}                  # the organizer's sample cases, as the files give them (never edited)
        for cid, fname in ORGANIZER_FILES.items():
            txt = (self.dir / "sources/organizer" / fname).read_text(encoding="utf-8")
            self.organizer_cases[cid] = json.loads(re.search(r"```json\n(.*?)\n```", txt, re.S).group(1))
        self.disp001, self.disp003 = self.organizer_cases["DISP-001"], self.organizer_cases["DISP-003"]
        self.precedents = {p["id"]: p for p in self.y["precedents"]["precedents"]}
        self.expected = {c["id"]: c for c in self.y["organizer_cases"]["cases"]}
        self.articles = {str(a["id"]): a for a in self.corpus["articles"]}
        self.version = str(self.y["rules"]["meta"]["version"])             # e.g. 0.2.0; names the workbooks (v0.2)
        self.vtag = "v" + ".".join(self.version.split(".")[:2])
        self._build_indexes()

    # ------------------------------------------------------------------ indexes
    def _build_indexes(self):
        tax = self.y["taxonomy"]
        self.vocab = {}            # vocab id -> {code: value dict}
        self.vocab_meta = {}       # vocab id -> vocabulary dict (without values)
        for v in tax["vocabularies"]:
            entries = {}

            def walk(vals, parent=None, level=None):
                for x in vals:
                    item = dict(x)
                    item["_parent"] = parent
                    entries[str(item["code"])] = item
                    if "children" in item:
                        walk(item["children"], item["code"])
            walk(v["values"])
            self.vocab[v["id"]] = entries
            self.vocab_meta[v["id"]] = {k: val for k, val in v.items() if k != "values"}
        self.case_leaves = {c: x for c, x in self.vocab["TX-CASE"].items() if x.get("level") != "category"}
        self.case_categories = {c: x for c, x in self.vocab["TX-CASE"].items() if x.get("level") == "category"}

        self.rules = {r["id"]: r for r in self.y["rules"]["rules"]}
        self.rule_order = [r["id"] for r in self.y["rules"]["rules"]]
        self.entities = {e["id"]: e for e in self.y["ontology"]["entities"]}
        self.entity_by_name = {e["name"]: e for e in self.y["ontology"]["entities"]}
        self.playbooks = {p["id"]: p for p in self.y["playbooks"]["playbooks"]}
        self.findings = {f["code"]: f for f in self.y["ontology"]["finding_types"]}
        self.state_machines = self.y["ontology"]["state_machines"]

        # source registry: declared documents + every Ryde Help Centre article in the corpus
        self.sources = {d["id"]: dict(d) for d in self.y["sources"]["documents"]}
        for aid, a in self.articles.items():
            self.sources[f"RYDE-{aid}"] = {
                "id": f"RYDE-{aid}", "title": a["title"], "publisher": "Ryde Technologies Pte Ltd",
                "type": "RYDE_POLICY", "url": a["url"], "date": a["edited_at"][:10],
                "created": a["created_at"][:10], "audience": a["audience"],
                "section": a.get("section_name"), "verify_against": f"corpus#{aid}",
                "credibility_default": "A" if a["edited_at"][:10] >= A_CUTOFF else "B",
            }

        # parameters
        ref = self.y["reference_data"]
        self.profiles = {name: prof["params"] for name, prof in ref["profiles"].items()}
        self.shared = ref["shared_params"]
        self.tables = ref["tables"]

    # ------------------------------------------------------------------ vocab helpers
    def resolve(self, vocab_id: str, raw):
        """Map a raw data value to a vocabulary code (case-insensitive, aliases, organizer codes)."""
        if raw is None:
            return None
        r = str(raw).strip()
        if vocab_id.startswith("SM-"):
            states = self.state_machines.get(vocab_id, [])
            for s in states:
                if s.lower() == r.lower():
                    return s
            return None
        for code, x in self.vocab.get(vocab_id, {}).items():
            if r == code or r.lower() == code.lower():
                return code
            if r.lower() in [str(a).lower() for a in x.get("aliases", []) or []]:
                return code
            if x.get("organizer_code") and r == x["organizer_code"]:
                return code
        return None

    def param(self, name: str, profile: str, overrides: dict | None = None):
        """Return the parameter entry (dict with value etc.) for a profile, applying overrides on the value."""
        if overrides and name in overrides:
            base = dict(self.param(name, profile) or {})
            base["value"] = overrides[name]
            base["overridden"] = True
            return base
        if name in self.profiles.get(profile, {}):
            return self.profiles[profile][name]
        fb = self.y["reference_data"]["profiles"].get(profile, {}).get("fallback_profile")
        if fb and name in self.profiles.get(fb, {}):          # META-01: what the case's policy object does not carry
            e = dict(self.profiles[fb][name])
            e["fallback_from"] = fb
            return e
        if name in self.shared:
            return self.shared[name]
        if name in self.tables:
            return self.tables[name]
        return None

    def pval(self, name: str, profile: str, overrides: dict | None = None):
        p = self.param(name, profile, overrides)
        return None if p is None else p.get("value")

    def param_exists(self, name: str) -> list[str]:
        where = [f"profile:{p}" for p, params in self.profiles.items() if name in params]
        if name in self.shared:
            where.append("shared")
        if name in self.tables:
            where.append("table")
        return where

    # ------------------------------------------------------------------ source text for quote checks
    @lru_cache(maxsize=None)
    def source_text(self, doc_id: str):
        """Return (normalized_text, raw_label) to verify quotes for a document, or (None, reason)."""
        d = self.sources.get(doc_id)
        if not d:
            return None, "unknown document id"
        va = d.get("verify_against")
        if not va:
            return None, "no local copy (paraphrase or reference only)"
        if va.startswith("corpus#"):
            a = self.articles[va.split("#", 1)[1]]
            return norm(a["title"] + "\n" + a["body_text"]), "corpus body"
        if va.endswith("#terms_of_use"):
            tou = self.corpus["terms_of_use"]
            return norm("\n".join(c["text"] for c in tou["clauses"])), "terms_of_use clauses"
        path = self.dir / va
        if not path.exists():
            return None, f"missing file {va}"
        return norm(path.read_text(encoding="utf-8")), va

    def article_key_statements(self, doc_id: str) -> str:
        if not doc_id.startswith("RYDE-") or doc_id == "RYDE-TOU":
            return ""
        a = self.articles.get(doc_id[5:])
        return norm("\n".join(a.get("key_statements") or [])) if a else ""

    def tou_clause_for(self, quote: str):
        q = norm(quote)
        for c in self.corpus["terms_of_use"]["clauses"]:
            if q in norm(c["text"]):
                return c
        return None


def expand_rule_refs(text: str) -> list[str]:
    """'AUTH-01 to AUTH-04, EXP-02' -> ['AUTH-01','AUTH-02','AUTH-03','AUTH-04','EXP-02']; 'CW-F02 or CW-F02B' -> both."""
    out = []
    for part in re.split(r",|\bor\b|\band\b", str(text)):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(.+?)(\d+)\s+to\s+(.+?)(\d+)$", part)
        if m and m.group(1) == m.group(3):
            width = len(m.group(2))
            for i in range(int(m.group(2)), int(m.group(4)) + 1):
                out.append(f"{m.group(1)}{str(i).zfill(width)}")
            continue
        out.extend(re.findall(r"\b[A-Z]{2,4}-[A-Z]?\d+[A-Z]?\b", part))
    return out


def leaf_paths(obj, prefix="", acc=None):
    """All leaf paths of a JSON object with their values; arrays are written as name[]."""
    if acc is None:
        acc = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            leaf_paths(v, f"{prefix}.{k}" if prefix else k, acc)
    elif isinstance(obj, list):
        for item in obj:
            leaf_paths(item, prefix + "[]", acc)
    else:
        acc.setdefault(prefix, []).append(obj)
    return acc


def collect_values(obj, path: str):
    """Values at a path like 'gps_telemetry[].status' or 'trip_data.pickup_location.lat'."""
    parts = path.split(".")
    cur = [obj]
    for part in parts:
        nxt = []
        is_arr = part.endswith("[]")
        key = part[:-2] if is_arr else part
        for c in cur:
            if isinstance(c, dict) and key in c:
                v = c[key]
                if is_arr and isinstance(v, list):
                    nxt.extend(v)
                else:
                    nxt.append(v)
        cur = nxt
    return cur

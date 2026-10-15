"""Stage 6: the verifier. It trusts nothing an agent wrote.

For the Judge's ruling:
  schema      the required fields are there, the outcome is in the engine vocabulary, the confidence is a number between 0 and 1
  citations   every cited evidence ID, rule ID, policy section and precedent exists (structured fields and every ID-like token in the prose);
              withheld evidence (account history) may not be cited (GEN-R03)
  numbers     the amount equals the engine's (outcome, amount, payer, payee when the engine states them); every number in a party explanation is
              a value of the case, the engine or the policy (EXP-03, kb/tools/explain.py exp03_check)
  engine      the Judge agrees with the engine, else gate G8: the case goes to a person with the full case file
  texts       no pseudonym codes, no fraud talk in a party explanation
For an advocate: the same citation checks. A brief is an argument, never evidence; invalid citations are listed and removed before the Judge reads it.

A citation, number or schema failure gets one retry with the verifier's feedback (config.JUDGE_MAX_RETRIES); a second failure is gate G7 (AUTH-04):
the engine's ruling stays as the provisional ruling at tier APPROVE.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from . import config
from .engine_stage import AMOUNT_OUTCOMES, RULING_OUTCOMES, jsonable
from .kbaccess import ORGANIZER_PROFILE, explain

EVID_RE = re.compile(r"(?<![A-Za-z0-9-])E-[A-Z]{3}-(?:\d{2}|[RD])(?![A-Za-z0-9-])")
RULE_RE = re.compile(r"(?<![A-Za-z0-9-])([A-Z]{2,4}-[A-Z]?\d+[A-Z]?)(?![A-Za-z0-9-])")
SECTION_RE = re.compile(r"(?:Sections?|§)\s*(\d+(?:\.\d+)?(?:(?:\s*,\s*|\s+and\s+|\s*&\s*|\s+to\s+)\d+(?:\.\d+)?)*)", re.I)
PRECEDENT_RE = re.compile(r"Precedents?\s+(\d+\.\d+)|PREC-(\d+\.\d+)", re.I)
NOT_RULES = {"DISP", "TRIP", "DEMO", "RIDER", "DRIVER", "PLATE", "ACCOUNT", "PHONE", "EMAIL", "CARD", "ID", "PREC", "LTA", "ORG"}
SOURCE_PREFIXES = {"RYDE"}
PSEUDONYM_CODE = re.compile(r"\b(?:RIDER|DRIVER)-(?:NAME-)?\d+\b|\bPLATE-[X\d]+\b|\bACCOUNT-X\b|\bPHONE-X\b|\bEMAIL-X\b")
JUDGE_REQUIRED = ["outcome", "amount_sgd", "payer", "payee", "confidence", "tier", "policy_sections", "rules", "evidence", "precedents", "reasoning",
                  "rider_explanation", "driver_explanation"]
OUTCOMES = RULING_OUTCOMES | {"ESCALATE_HUMAN", "REQUEST_INFO"}
PARTIES = {"RIDER", "DRIVER", "PLATFORM", None}


# ------------------------------------------------------------------ policy sections
def policy_sections() -> set[str]:
    text = config.POLICY_V21_PATH.read_text(encoding="utf-8")
    secs = {f"Section {m}" for m in re.findall(r"^## Section (\d+):", text, re.M)}
    secs |= {f"Section {m}" for m in re.findall(r"^### (\d+\.\d+) ", text, re.M)}
    secs |= {f"Precedent {m}" for m in re.findall(r"^### Precedent (\d+\.\d+):", text, re.M)}
    return secs


def normalize_section(s) -> str | None:
    s = str(s).strip()
    m = re.match(r"^(?:precedent|prec-?)\s*(\d+\.\d+)$", s, re.I)
    if m:
        return f"Precedent {m.group(1)}"
    m = re.match(r"^(?:sections?|sec\.?|§)?\s*(\d+(?:\.\d+)?)$", s, re.I)
    return f"Section {m.group(1)}" if m else None


@dataclass
class Check:
    name: str
    status: str                # PASS | FAIL | WARN | INFO
    detail: str
    kind: str = "info"         # schema | citation | number | engine | text | safety | confidence | info

    def to_dict(self):
        return {"name": self.name, "status": self.status, "detail": self.detail, "kind": self.kind}


@dataclass
class Context:
    kb: object
    profile: str
    evidence_ids: set
    withheld_ids: set
    rule_ids: set
    source_ids: set
    sections: set
    precedent_ids: set
    engine: dict
    allowed_numbers: set
    quotes: set
    pseudonym_check: bool = True


def build_context(kb, profile: str, items: list[dict], engine: dict, policy_text: str) -> Context:
    nums = set()

    def add(token: str):
        t = token.replace(",", "")
        forms = {token, t, t.lstrip("0") or "0"}
        if re.fullmatch(r"\d+(?:\.\d+)?", t):
            f = float(t)
            forms |= {f"{f:.2f}", f"{f:.1f}", f"{f:.0f}", str(int(f)) if f.is_integer() else t}
            if f.is_integer() and f >= 1000:
                forms.add(f"{int(f):,}")
        for x in list(forms):
            nums.add(x)
            nums.add("S$" + x)
        if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", token):
            for part in token.split(":"):
                add(part)
    blobs = [json.dumps(it["data"], ensure_ascii=False) + " " + str(it["ts"] or "") + " " + str(it["summary"]) for it in items if not it["withheld"]]
    blobs += [json.dumps(jsonable({k: v for k, v in engine.items() if k != "reviewer_only"}), ensure_ascii=False)]
    blobs += [policy_text]
    for blob in blobs:
        for tok in explain.NUM_RE.findall(blob):
            add(tok)
    for e in kb.profiles.get(profile, {}).values():
        v = e.get("value")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            add(str(v))
    return Context(kb=kb, profile=profile, evidence_ids={it["id"] for it in items if not it["withheld"]}, withheld_ids={it["id"] for it in items if it["withheld"]},
                   rule_ids=set(kb.rules), source_ids=set(kb.sources), sections=policy_sections(), precedent_ids={"Precedent " + p["section"].split()[-1] for p in kb.precedents.values()},
                   engine=engine, allowed_numbers=nums, quotes=explain.clause_quotes(kb))


# ------------------------------------------------------------------ citations
def scan_prose(ctx: Context, text: str) -> dict:
    """Every ID-like token in a text, by kind."""
    t = text or ""
    ev = sorted(set(EVID_RE.findall(t)))
    rules, sources = [], []
    for m in RULE_RE.findall(t):
        prefix = m.split("-")[0]
        if prefix in NOT_RULES:
            continue
        (sources if prefix in SOURCE_PREFIXES else rules).append(m)
    secs = []
    if ctx.profile == ORGANIZER_PROFILE:
        for m in SECTION_RE.findall(t):
            secs += [f"Section {n}" for n in re.findall(r"\d+(?:\.\d+)?", m)]
    precs = [f"Precedent {a or b}" for a, b in PRECEDENT_RE.findall(t)]
    return {"evidence": ev, "rules": sorted(set(rules)), "sources": sorted(set(f"{s}" for s in sources)), "sections": sorted(set(secs)), "precedents": sorted(set(precs))}


def check_cited(ctx: Context, cited: dict, where: str) -> tuple[list[Check], dict]:
    """cited: {"evidence": [...], "rules": [...], "sections": [...], "precedents": [...]} from structured fields and prose. Returns checks and the invalid IDs."""
    bad = {"evidence": [], "withheld": [], "rules": [], "sections": [], "precedents": []}
    for e in cited.get("evidence", []):
        if e in ctx.withheld_ids:
            bad["withheld"].append(e)
        elif e not in ctx.evidence_ids:
            bad["evidence"].append(e)
    bad["rules"] = [r for r in cited.get("rules", []) if r not in ctx.rule_ids]
    for s in cited.get("sections", []):
        if ctx.profile == ORGANIZER_PROFILE:
            n = normalize_section(s)
            if n not in ctx.sections and s not in ctx.source_ids and s not in ctx.rule_ids:
                bad["sections"].append(s)
        elif s not in ctx.source_ids and s not in ctx.rule_ids:
            bad["sections"].append(s)
    for p in cited.get("precedents", []):
        n = normalize_section(p)
        if n not in ctx.precedent_ids or ctx.profile != ORGANIZER_PROFILE:
            bad["precedents"].append(p)
    checks = []
    labels = {"evidence": "evidence IDs that do not exist", "withheld": "withheld evidence (account history is closed to agents, GEN-R03)", "rules": "rule IDs that do not exist",
              "sections": "policy sections that do not exist", "precedents": "precedents that do not exist"}
    for k, label in labels.items():
        if bad[k]:
            checks.append(Check(f"{where}: {k}", "FAIL", f"cites {label}: {', '.join(sorted(set(map(str, bad[k]))))}", "citation"))
    if not checks:
        n = sum(len(v) for v in cited.values())
        checks.append(Check(f"{where}: citations", "PASS", f"{n} cited ID(s) all exist", "citation"))
    return checks, bad


def _merge(a: dict, b: dict) -> dict:
    return {k: sorted(set(a.get(k, [])) | set(b.get(k, []))) for k in ("evidence", "rules", "sections", "precedents")}


def _structured(d: dict, ev="evidence", rules="rules", secs="policy_sections", precs="precedents") -> dict:
    def lst(x):
        return [str(i) for i in x] if isinstance(x, list) else []
    return {"evidence": lst(d.get(ev)), "rules": lst(d.get(rules)), "sections": lst(d.get(secs)), "precedents": lst(d.get(precs))}


# ------------------------------------------------------------------ advocates
def verify_advocate(ctx: Context, brief: dict, party: str) -> dict:
    cited = _structured({}, )
    args = brief.get("arguments") or []
    for a in args if isinstance(args, list) else []:
        if isinstance(a, dict):
            cited = _merge(cited, _structured(a))
    for key in ("rebuttals", "concessions", "weaknesses"):
        for a in brief.get(key) or []:
            if isinstance(a, dict):
                cited = _merge(cited, _structured(a))
    prose = " ".join(str(brief.get(k, "")) for k in ("brief", "stance", "requested_outcome"))
    found = scan_prose(ctx, prose)
    cited = _merge(cited, {"evidence": found["evidence"], "rules": found["rules"] + [s for s in found["sources"]], "sections": found["sections"], "precedents": found["precedents"]})
    checks, bad = check_cited(ctx, cited, f"{party} advocate")
    return {"checks": [c.to_dict() for c in checks], "invalid": bad, "ok": not any(c.status == "FAIL" for c in checks), "cited": cited}


def strip_invalid(brief: dict, bad: dict) -> dict:
    """The brief as the Judge reads it: citations that do not exist are removed from the structured fields (they stay in the prose, flagged by the verifier)."""
    drop = {"evidence": set(bad["evidence"]) | set(bad["withheld"]), "rules": set(bad["rules"]), "policy_sections": set(bad["sections"]), "precedents": set(bad["precedents"])}
    out = json.loads(json.dumps(brief))
    for key in ("arguments", "rebuttals", "concessions", "weaknesses"):
        for a in out.get(key) or []:
            if isinstance(a, dict):
                for field_, bad_set in drop.items():
                    if isinstance(a.get(field_), list):
                        a[field_] = [x for x in a[field_] if x not in bad_set]
    return out


# ------------------------------------------------------------------ the Judge
def _num_eq(a, b) -> bool:
    return abs(float(a) - float(b)) <= 0.005


def numbers_unmatched(text: str, allowed: set, quotes: set) -> list[str]:
    """EXP-03 as explain.exp03_check, with one fix: a number followed by a comma ('at 08:51, and') is the number, not '51,' (kb/open_items.yaml D59 (g))."""
    def exempt(m):
        span = " ".join((m.group(1) or m.group(2)).split())
        return " " if len(re.findall(r"[A-Za-z]{2,}", span)) >= 3 and any(span in q for q in quotes) else m.group(0)
    text = explain.QUOTE_RE.sub(exempt, text)
    toks = [n.rstrip(",") for n in explain.NUM_RE.findall(explain.ID_RE.sub(" ", text))]
    return [n for n in toks if n and n not in allowed]


def compare_with_engine(engine: dict, j: dict) -> list[str]:
    """What differs between the Judge's ruling and the engine's (empty when they agree)."""
    diffs = []
    if j.get("outcome") != engine["outcome"]:
        diffs.append(f"outcome {j.get('outcome')} against the engine's {engine['outcome']}")
    e_amt = engine["amount_sgd"] if engine["amount_sgd"] not in (None, 0, 0.0) else None
    j_amt = j.get("amount_sgd") if j.get("amount_sgd") not in (None, 0, 0.0) else None
    if (e_amt is None) != (j_amt is None) or (e_amt is not None and not _num_eq(e_amt, j_amt)):
        diffs.append(f"amount {j.get('amount_sgd')} against the engine's {engine['amount_sgd']}")
    for k in ("payer", "payee"):
        want = engine.get(k)
        got = (str(j.get(k)).upper() if j.get(k) else None)
        got = "PLATFORM" if got == "RYDE" else got
        if want and got != want:
            diffs.append(f"{k} {got} against the engine's {want}")
    return diffs


def verify_judge(ctx: Context, j: dict) -> dict:
    checks: list[Check] = []
    missing = [f for f in JUDGE_REQUIRED if f not in j]
    if missing:
        checks.append(Check("schema", "FAIL", f"missing fields: {', '.join(missing)}", "schema"))
    if j.get("outcome") not in OUTCOMES:
        checks.append(Check("schema: outcome", "FAIL", f"outcome {j.get('outcome')!r} is not one of {sorted(OUTCOMES)}", "schema"))
    conf = j.get("confidence")
    if isinstance(conf, bool) or not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
        checks.append(Check("schema: confidence", "FAIL", f"confidence {conf!r} is not a number between 0 and 1", "schema"))
    amt = j.get("amount_sgd")
    if amt is not None and (isinstance(amt, bool) or not isinstance(amt, (int, float))):
        checks.append(Check("schema: amount", "FAIL", f"amount_sgd {amt!r} is not a number or null", "schema"))
    for k in ("payer", "payee"):
        v = j.get(k)
        if (str(v).upper() if v else None) not in PARTIES | {"RYDE"}:
            checks.append(Check(f"schema: {k}", "FAIL", f"{k} {v!r} is not RIDER, DRIVER, PLATFORM or null", "schema"))
    for k in ("policy_sections", "rules", "evidence", "precedents"):
        if k in j and not isinstance(j[k], list):
            checks.append(Check(f"schema: {k}", "FAIL", f"{k} must be a list", "schema"))
    if not any(c.status == "FAIL" and c.kind == "schema" for c in checks):
        checks.append(Check("schema", "PASS", "all required fields are present and well formed", "schema"))

    # citations: structured fields plus every ID in the prose
    cited = _structured(j)
    prose_fields = ("reasoning", "rider_explanation", "driver_explanation", "disagreement_note")
    for f_ in prose_fields:
        found = scan_prose(ctx, str(j.get(f_) or ""))
        cited = _merge(cited, {"evidence": found["evidence"], "rules": found["rules"] + found["sources"], "sections": found["sections"], "precedents": found["precedents"]})
    cchecks, bad = check_cited(ctx, cited, "Judge")
    checks += cchecks

    # numbers in the party explanations (EXP-03) and the reasoning (warning only)
    c = j.get("confidence") if isinstance(j.get("confidence"), (int, float)) and not isinstance(j.get("confidence"), bool) else None
    allowed = set(ctx.allowed_numbers)
    if c is not None:
        allowed |= {f"{c:.2f}", f"{round(c * 100)}", f"{c * 100:.0f}", f"{c * 100:.1f}"}
    unmatched = {}
    for f_ in ("rider_explanation", "driver_explanation"):
        text = str(j.get(f_) or "")
        if not text.strip():
            checks.append(Check(f"text: {f_}", "FAIL", "the explanation is empty", "text"))
            continue
        un = numbers_unmatched(text, allowed, ctx.quotes)
        if un:
            unmatched[f_] = sorted(set(un))
        if PSEUDONYM_CODE.search(text):
            checks.append(Check(f"text: {f_}", "FAIL", "the explanation contains a pseudonym code; parties are 'you', 'the rider' and 'the driver'", "text"))
        if re.search(r"\bfraud", text, re.I):
            checks.append(Check(f"text: {f_}", "FAIL", "a party explanation must not mention fraud signals (reviewer only, FRD-01)", "text"))
    if unmatched:
        checks.append(Check("numbers", "FAIL", "numbers in the explanations that are not a value of the case, the engine or the policy: "
                            + "; ".join(f"{k}: {', '.join(v)}" for k, v in unmatched.items()), "number"))
    else:
        checks.append(Check("numbers", "PASS", "every number in both explanations is a value of the case, the engine or the policy (EXP-03)", "number"))
    un_r = numbers_unmatched(str(j.get("reasoning") or ""), allowed, ctx.quotes)
    if un_r:
        checks.append(Check("numbers: reasoning", "WARN", f"numbers in the reasoning that are not registered values: {', '.join(sorted(set(un_r)))}", "number"))

    # agreement with the engine
    diffs = compare_with_engine(ctx.engine, j) if not any(c_.status == "FAIL" and c_.kind == "schema" for c_ in checks) else []
    if not any(c_.status == "FAIL" and c_.kind == "schema" for c_ in checks):
        checks.append(Check("engine", "FAIL" if diffs else "PASS",
                            ("the Judge disagrees with the rules engine: " + "; ".join(diffs)) if diffs else "outcome, amount, payer and payee equal the engine's", "engine"))
    failures = [c_ for c_ in checks if c_.status == "FAIL"]
    soft = [c_ for c_ in failures if c_.kind in ("schema", "citation", "number", "text")]
    feedback = "; ".join(c_.detail for c_ in soft)
    return {"checks": [c_.to_dict() for c_ in checks], "ok": not failures, "retryable_failure": bool(soft), "engine_diffs": diffs, "disagrees": bool(diffs), "invalid": bad,
            "feedback": feedback, "safety_concern": bool(j.get("safety_concern")), "cited": cited}


def verify_case_file(ctx: Context, cf: dict) -> dict:
    """The Judge's case file (safety or no-engine mode): citations only; it has no outcome to check."""
    cited = {"evidence": [], "rules": [], "sections": [], "precedents": []}
    for key in ("evidence",):
        cited["evidence"] += [str(x) for x in cf.get(key) or []]
    for t in cf.get("timeline") or []:
        if isinstance(t, dict):
            cited["evidence"] += [str(x) for x in t.get("evidence") or []]
    for t in cf.get("disputed_points") or []:
        if isinstance(t, dict):
            cited["evidence"] += [str(x) for x in t.get("evidence") or []]
    prose = " ".join(str(cf.get(k, "")) for k in ("case_summary",))
    found = scan_prose(ctx, prose)
    cited = _merge(cited, {"evidence": found["evidence"], "rules": found["rules"], "sections": found["sections"], "precedents": found["precedents"]})
    checks, bad = check_cited(ctx, cited, "Judge case file")
    return {"checks": [c.to_dict() for c in checks], "ok": not any(c.status == "FAIL" for c in checks), "invalid": bad, "cited": cited}

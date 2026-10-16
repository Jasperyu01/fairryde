"""Stage 1: intake and classification (CLS rules), deterministic.

CLS-05  the organizer's dispute code -> a taxonomy leaf (fare_dispute is FC-SURGE only with surge evidence, else FC-FAREMISMATCH)
META-01 the policy profile (organizer_v2_1 for a DISP-nnn case, organizer_case for a case that embeds its own policy, else ryde_2026)
CLS-01  safety content, by the engines' offline stand-in for the reading (a keyword list); policy v2.1 Section 5.2 treats any hit as a
        case-file-only case. The agents add a second look by meaning (a safety_concern flag), see verifier.py.
GEN-R04 instruction-like text in a party's words is flagged and ignored
GEN-R07 a claim type without a reference engine goes to a person with the case file

The result says which route the case takes: ENGINE (a reference engine rules), CASE_FILE (agents prepare a case file, no ruling).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .kbaccess import ORGANIZER_PROFILE, case_adapter, engine_noshow as E, kbload

SAFETY_LEAF_PREFIX = "SE-"


@dataclass
class Classification:
    case_id: str
    dispute_type_raw: str
    taxonomy_code: str | None
    claim_type: str | None
    claim_label: str | None
    profile: str
    profile_reason: str
    filed_by: str
    engine: str | None                      # engine_noshow | engine_route | engine_surge | engine_toll | None
    route: str                              # ENGINE | CASE_FILE
    case_file_reason: str | None            # SAFETY | NO_ENGINE | None
    safety: dict = field(default_factory=dict)
    injection_authors: list = field(default_factory=list)
    rules_fired: list = field(default_factory=list)       # [{"rule", "name", "result"}]
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def engine_for(kb, canon: dict, profile: str) -> str | None:
    """Which reference engine rules this case, mirroring engines.run_case (a test keeps the two in step). None means no engine exists."""
    raw = canon["dispute_ticket"]["dispute_type"]
    if raw == "erp_toll":
        return "engine_toll"
    code = kb.resolve("TX-CASE", raw)
    if code == "FC-SURGE":
        from .kbaccess import engine_surge
        if not engine_surge.has_surge_evidence(canon):
            code = "FC-FAREMISMATCH"
    if code == "CW-NOSHOW":
        return "engine_noshow"
    if code == "FC-ROUTE" and profile == ORGANIZER_PROFILE:
        return "engine_route"
    if code in ("FC-SURGE", "FC-FAREMISMATCH") and profile == ORGANIZER_PROFILE:
        return "engine_surge"
    return None


def classify(kb, raw_case: dict, case_id: str, profile_override: str | None = None) -> Classification:
    canon, _reference = case_adapter.prepare(raw_case)       # the organizer's own analysis blocks never reach a rule or an agent
    tk = canon["dispute_ticket"]
    rules: list[dict] = []

    def fire(rid: str, result: str):
        rules.append({"rule": rid, "name": kb.rules[rid]["name"] if rid in kb.rules else rid, "result": result})

    profile = profile_override or kbload.default_profile(canon)
    reason = ("organizer case (a DISP-nnn id): policy v2.1 governs" if profile == ORGANIZER_PROFILE else
              "the case embeds its own policy object (legacy profile organizer_case)" if profile == "organizer_case" else
              "regression and synthetic cases run on Ryde's published policy (profile ryde_2026)")
    if profile_override and profile_override != kbload.default_profile(canon):
        reason = "set by the app for this case (an uploaded case or the synthetic demo runs under policy v2.1)"
    fire("META-01", f"profile {profile}: {reason}")

    raw = tk["dispute_type"]
    code = kb.resolve("TX-CASE", raw)
    claim = code
    if code == "FC-SURGE":
        from .kbaccess import engine_surge
        if not engine_surge.has_surge_evidence(canon):
            claim = "FC-FAREMISMATCH"
    if raw == "erp_toll":
        claim = "FC-TOLL"
    leaf = kb.vocab["TX-CASE"].get(claim or "", {})
    fire("CLS-05", f"dispute_type {raw!r} -> {claim or 'no taxonomy leaf (the organizer code is not in the taxonomy)'}")

    chat_texts = [c.get("content") or c.get("message") or "" for c in (canon.get("chat_logs") or []) if c.get("type", "message") == "message"]
    texts = [tk.get("description", "") or ""] + chat_texts
    safety_hits = E.safety_hits(texts)
    disc_hits = E.discrimination_hits(texts)
    is_se_leaf = (claim or "").startswith(SAFETY_LEAF_PREFIX)
    safety = {"flag": bool(safety_hits or disc_hits or is_se_leaf), "keyword_hits": len(set(safety_hits) | set(disc_hits)),
              "discrimination": bool(disc_hits), "taxonomy_safety_leaf": is_se_leaf}
    if safety["flag"]:
        fire("CLS-01", "safety content found" + (" (the taxonomy leaf is a safety type)" if is_se_leaf else f" ({safety['keyword_hits']} keyword hit(s))")
             + ": policy v2.1 Section 5.2, the agents prepare a case file and rule on nothing")
    else:
        fire("CLS-01", "no safety content found by the keyword stand-in (the agents look again by meaning)")

    injected = sorted({who for who, text in [(kb.resolve("TX-ROLE", tk.get("filed_by")) or "OTHER", tk.get("description", "") or "")]
                       + [(kb.resolve("TX-ROLE", c.get("sender")) or "OTHER", c.get("content") or c.get("message") or "")
                          for c in (canon.get("chat_logs") or []) if c.get("type", "message") == "message"]
                       if any(re.search(p, text, re.I) for p in E.INJECTION_PATTERNS)})
    fire("GEN-R04", f"instruction-like text from {', '.join(injected)} flagged and ignored" if injected else "no instructions found in party text")

    engine = engine_for(kb, canon, profile)
    route, why = "ENGINE", None
    if safety["flag"]:
        route, why = "CASE_FILE", "SAFETY"
        fire("SE-R01", "a person decides; FairRyde proposes no outcome, amount or measure (policy v2.1 Section 5.2)")
    elif engine is None:
        route, why = "CASE_FILE", "NO_ENGINE"
        fire("GEN-R07", f"no reference engine for {claim or 'this dispute type'} under {profile}: no written rule decides it in code, a person decides with the case file")
    notes = []
    if claim and leaf.get("scope") in ("TRIAGE_TO_HUMAN",) and not safety["flag"]:
        notes.append(f"taxonomy scope of {claim} is {leaf['scope']}")
    return Classification(case_id=case_id, dispute_type_raw=raw, taxonomy_code=code, claim_type=claim, claim_label=leaf.get("label"),
                          profile=profile, profile_reason=reason, filed_by=kb.resolve("TX-ROLE", tk.get("filed_by")) or str(tk.get("filed_by")),
                          engine=engine, route=route, case_file_reason=why, safety=safety, injection_authors=injected, rules_fired=rules, notes=notes)

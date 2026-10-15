"""The three LLM agents: Rider Advocate, Driver Advocate, Judge.

Each agent has its own prompt file in app/prompts/ (a shared preamble, then a ruling-mode and a case-file-mode section). What an agent sees:
  - the system message: its prompt, then the policy (policy v2.1 in full for an organizer case; the rule cards of the case's rules otherwise);
  - the user message: one JSON case file built from the evidence items, the engine facts, the valid IDs, and (for the Driver Advocate and the
    Judge) the earlier agents' briefs, marked as arguments.
Advocates get the engine's facts but not its outcome, amount or tier. The Judge gets the engine result without anything about account history.
Everything is pseudonymized before it is built into the request, and the finished request strings pass the privacy boundary check (privacy.py).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from . import config, engine_stage, evidence as ev, privacy
from .verifier import policy_sections

AGENT_ROLE = {"rider_advocate": "Rider Advocate", "driver_advocate": "Driver Advocate", "judge": "Judge"}
MODE_MARKERS = {"ruling": "<!-- RULING MODE -->", "case_file": "<!-- CASE FILE MODE -->"}


class AgentOutputError(ValueError):
    pass


def load_prompt(agent: str, mode: str) -> str:
    text = (config.PROMPTS_DIR / f"{agent}.md").read_text(encoding="utf-8")
    markers = sorted((text.index(m), k, m) for k, m in MODE_MARKERS.items())
    pre = text[:markers[0][0]].rstrip()
    sections = {}
    for i, (pos, key, marker) in enumerate(markers):
        end = markers[i + 1][0] if i + 1 < len(markers) else len(text)
        sections[key] = text[pos + len(marker):end].strip()
    return pre + "\n\n" + sections[mode]


def policy_context(kb, profile: str, out: dict, cls) -> str:
    """The policy the agents read: policy v2.1 in full for an organizer case, else the cards of the rules involved with their sources."""
    if profile == "organizer_v2_1":
        return "# Reference policy: Ryde Dispute Resolution Policy v2.1\nCite sections as \"Section 1.3\" and precedents as \"Precedent 7.1\".\n\n" + config.POLICY_V21_PATH.read_text(encoding="utf-8")
    ids = list(dict.fromkeys(engine_stage.agent_rules(out) + [r["rule"] for r in cls.rules_fired if r["rule"] in kb.rules]))
    cards = []
    for rid in ids:
        r = kb.rules.get(rid)
        if not r:
            continue
        srcs = [s for s in r.get("sources", []) if s.get("profile") in (None, "", profile)] or r.get("sources", [])
        src_txt = "; ".join(f"{s['doc']}: \"{str(s.get('quote', ''))[:200]}\"" for s in srcs[:3])
        cards.append(f"### {rid} {r['name']} (credibility {r['credibility']})\n{str(r['statement']).strip()[:1400]}\nSources: {src_txt}")
    return (f"# Reference rules (profile {profile})\nThis case is ruled on Ryde's published policy as FairRyde's rule cards state it, not on policy v2.1. Cite rule IDs such as \"CW-R03\" "
            "and source documents such as \"RYDE-23534478435353\" (the `doc` of a card's source).\n\n" + "\n\n".join(cards))


def valid_ids(kb, profile: str, items: list[dict], out: dict, cls) -> dict:
    rules = list(dict.fromkeys(engine_stage.agent_rules(out) + [r["rule"] for r in cls.rules_fired if r["rule"] in kb.rules]))
    d = {"evidence": [i["id"] for i in items if not i["withheld"]], "rules": rules}
    if profile == "organizer_v2_1":
        d["policy_sections"] = sorted(policy_sections(), key=lambda s: [int(x) if x.isdigit() else x for x in re.split(r"[ .]", s)])
        d["precedents"] = sorted("Precedent " + p["section"].split()[-1] for p in kb.precedents.values())
    else:
        docs = []
        for rid in rules:
            for s in kb.rules[rid].get("sources", []):
                if s.get("doc") and s["doc"] in kb.sources and s["doc"] not in docs:
                    docs.append(s["doc"])
        d["policy_sections"] = docs
        d["precedents"] = []
    return d


def precedent_view(kb, out: dict) -> list[dict]:
    rows = []
    for p in out.get("precedents") or []:
        rec = kb.precedents.get(p["id"], {})
        rows.append({"cite_as": "Precedent " + p["section"].split()[-1], "case_id": p["case_id"], "match": "ALIGNED" if p["aligned"] else "DISTINGUISHED",
                     "same_key_factors": p["same"], "differing_key_factors": p["differs"], "facts": rec.get("facts"), "ruling": rec.get("ruling"),
                     "outcome": p["outcome"], "refund_amount_sgd": p["refund_amount_sgd"], "confidence": p["confidence"]})
    return rows


@dataclass
class Run:
    """Everything the agents need for one case."""
    case_id: str
    kb: object
    cls: object
    items: list
    out: dict
    mode: str                    # ruling | case_file
    terms: list
    policy_text: str
    ids: dict

    @property
    def case_view(self) -> dict:
        return {"case_id": self.case_id, "profile": self.cls.profile,
                "claim": {"type": self.cls.claim_type, "label": self.cls.claim_label, "filed_by": self.cls.filed_by, "raw_dispute_type": self.cls.dispute_type_raw},
                "mode": self.mode, "case_file_reason": self.out.get("case_file_reason") if self.mode == "case_file" else None,
                "evidence": ev.agent_view(self.items), "valid_ids": self.ids}


def build_request(run: Run, agent: str, *, rider_brief=None, driver_brief=None, retry_feedback: str | None = None, rider_check=None, driver_check=None) -> tuple[list, str]:
    """(system blocks, user message), pseudonymized."""
    view = run.case_view
    if agent == "judge":
        payload = {**view, "engine_result": engine_stage.judge_view(run.out), "precedents": precedent_view(run.kb, run.out) if run.cls.profile == "organizer_v2_1" else [],
                   "briefs": {"rider_advocate": rider_brief, "driver_advocate": driver_brief,
                              "note": "These briefs are arguments, never evidence.",
                              "citation_check": {"rider_advocate": (rider_check or {}).get("invalid"), "driver_advocate": (driver_check or {}).get("invalid")}}}
        if run.mode == "case_file":
            payload["engine_result"] = {"claim_type": run.out["claim_type"], "profile": run.out["profile"], "reasons": run.out["reasons"], "rules": engine_stage.agent_rules(run.out),
                                        "findings": run.out["findings"], "secondary_claim_note": "A contested charge, if any, is a secondary claim recorded in the file; no view on it."}
            payload["precedents"] = []
    else:
        payload = {**view, "engine_facts": engine_stage.advocate_view(run.out)}
        if run.mode == "case_file":
            payload["engine_facts"] = {"claim_type": run.out["claim_type"], "findings": run.out["findings"]}
        if agent == "driver_advocate":
            payload["rider_advocate_brief"] = {"argument_only": True, **(rider_brief or {})}
    if retry_feedback:
        payload["verifier_feedback"] = ("Your previous answer failed verification: " + retry_feedback + ". Return the complete corrected JSON object. "
                                        "Use only the IDs in valid_ids and only numbers that appear in the case file, the engine result or the policy.")
    instruction = {"rider_advocate": "Write the Rider Advocate's answer now.", "driver_advocate": "Write the Driver Advocate's answer now.", "judge": "Write the Judge's answer now."}[agent]
    safe = privacy.pseudonymize(payload, run.terms)
    user = "<case_file>\n" + json.dumps(safe, ensure_ascii=False, indent=1) + "\n</case_file>\n\n" + instruction + " Reply with one JSON object only."
    prompt = privacy.pseudonymize(load_prompt(agent, run.mode), run.terms)
    system = [{"type": "text", "text": prompt}, {"type": "text", "text": run.policy_text, "cache_control": {"type": "ephemeral"}}]
    return system, user


def parse_json(text: str) -> dict:
    """The JSON object in a model reply (tolerates a code fence or a sentence around it)."""
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        v = json.loads(t)
    except json.JSONDecodeError:
        i, j = t.find("{"), t.rfind("}")
        if i < 0 or j <= i:
            raise AgentOutputError("the reply holds no JSON object") from None
        try:
            v = json.loads(t[i:j + 1])
        except json.JSONDecodeError as exc:
            raise AgentOutputError(f"the reply is not valid JSON ({exc.msg})") from None
    if not isinstance(v, dict):
        raise AgentOutputError("the reply is JSON but not an object")
    return v


def call_agent(client, run: Run, agent: str, *, attempt: int = 0, **kw) -> dict:
    """One agent turn: build the request, pass the privacy boundary, call the model, parse the reply. Never raises for a model-side problem."""
    system, user = build_request(run, agent, **kw)
    counts = privacy.assert_clean([b["text"] for b in system] + [user], run.terms)         # PrivacyError stops the run: nothing leaves the machine
    msg = {"agent": agent, "role": AGENT_ROLE[agent], "mode": run.mode, "attempt": attempt, "model": None, "client": client.name, "json": None, "text": "", "error": None,
           "refused": False, "usage": {}, "latency_s": 0.0, "privacy_boundary": counts, "request_chars": len(user) + sum(len(b["text"]) for b in system)}
    res = client.complete(agent=agent, system_blocks=system, user=user, case_id=run.case_id, attempt=attempt, mode=run.mode)
    msg.update(model=res.model, usage=res.usage, latency_s=res.latency_s, refused=res.refused, request_id=res.request_id, text=res.text, error=res.error, mock=res.mock)
    if res.error or res.refused:
        return msg
    try:
        msg["json"] = parse_json(res.text)
    except AgentOutputError as exc:
        msg["error"] = f"unreadable reply: {exc}"
        if not res.mock and attempt == 0:           # one repair attempt in live mode
            fix = client.complete(agent=agent, system_blocks=system, user=user + "\n\nYour previous reply could not be read as JSON (" + str(exc) + "). Reply with one JSON object only.",
                                  case_id=run.case_id, attempt=attempt, mode=run.mode)
            msg["usage"] = {k: (msg["usage"].get(k) or 0) + ((fix.usage or {}).get(k) or 0) for k in set(msg["usage"]) | set(fix.usage or {})}
            try:
                msg["json"], msg["text"], msg["error"] = parse_json(fix.text), fix.text, None
            except AgentOutputError as exc2:
                msg["error"] = f"unreadable reply after one repair: {exc2}"
    return msg


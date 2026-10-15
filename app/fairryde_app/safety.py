"""Policy v2.1 Section 5.2 and CLS-01 / SE-R01: on a safety case the agents gather evidence, summarize accounts and prepare the case file.
They cannot issue a ruling, determine fault or recommend a resolution.

The prompts say so; this module enforces it afterwards. lint() finds sentences in agent text that read as a ruling, a finding of fault or a
recommendation, and redact() removes them from what the app shows and stores. The structured output of a case-file agent has no outcome,
amount or measure at all, and the final ruling of a safety case is fixed by the pipeline (ESCALATE_HUMAN, no amount, tier HUMAN).
"""
from __future__ import annotations

import re

FORBIDDEN = [
    r"\brecommend\w*", r"\bsuggest\w* (?:that|a|an|the)\b", r"\bshould (?:not )?(?:be|have|receive|get|pay|refund|face|lose)\b", r"\bought (?:not )?to\b",
    r"\bmust (?:be|pay|refund|face)\b", r"\bat fault\b", r"\b(?:is|are|was|were) (?:guilty|liable|to blame|responsible for|in the wrong)\b", r"\bblame\w*",
    r"\bnegligen\w+", r"\bin the wrong\b", r"\b(?:i|we) (?:rule|find|conclude|decide|determine)\b",
    r"\b(?:refund|compensat\w+|suspen\w+|ban(?:ned)?|deactivat\w+|penali[sz]\w+|terminat\w+)\b[^.]{0,30}\b(?:is|are|should|shall|will be|be|granted|awarded)\b",
    r"\b(?:uphold|reject|dismiss|grant)\w*\b[^.]{0,12}\b(?:claim|complaint|dispute|charge|fee)\b", r"\bverdict\b", r"\bfavou?rs? the (?:rider|driver)\b",
]
FORBIDDEN_RE = [re.compile(p, re.I) for p in FORBIDDEN]
SPLIT = re.compile(r"(?<=[.!?])\s+")
REDACTED = "[removed: a safety case file proposes no ruling, finding of fault or recommendation (policy v2.1 Section 5.2)]"

SAFETY_NOTICE = ("The case includes a safety concern, so a Ryde staff member will review the whole case and decide it. FairRyde prepares the case file only and proposes no outcome, "
                 "amount or measure (Section 5.2).")
NO_RULE_NOTICE = ("No written rule in this version of FairRyde decides this kind of case, so a Ryde staff member will decide it. FairRyde has prepared the case file with the evidence "
                  "and both accounts and proposes no outcome or amount (GEN-R07).")


def lint(text: str) -> list[str]:
    """The sentences of the text that read as a ruling, a finding of fault or a recommendation."""
    return [s for s in SPLIT.split(text or "") if any(p.search(s) for p in FORBIDDEN_RE)]


def redact(text: str) -> tuple[str, int]:
    """The text with each offending sentence replaced by a marker, and how many were replaced."""
    out, n = [], 0
    for s in SPLIT.split(text or ""):
        if any(p.search(s) for p in FORBIDDEN_RE):
            out.append(REDACTED)
            n += 1
        else:
            out.append(s)
    return " ".join(out), n


def redact_obj(o):
    """Redact every string of a JSON-like object. Returns (object, total replaced)."""
    total = 0

    def walk(x):
        nonlocal total
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v) for v in x]
        if isinstance(x, str) and len(x) > 25:
            y, n = redact(x)
            total += n
            return y
        return x
    return walk(o), total

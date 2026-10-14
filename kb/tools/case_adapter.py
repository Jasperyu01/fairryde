"""Read an organizer sample case in the form the engines expect, and keep the organizer's own answer out of the engines.

DISP-001 and DISP-003 (uploaded 14 Oct 2026) differ from DISP-002 in a few ways: a chat log entry has the key "message" and no "type"
(DISP-002 has "content" and "type"), there are no app events, and DISP-001 carries blocks that are the organizer's own analysis and expected
ruling (case_metadata, chat_log_analysis, traffic_analysis, evidence_summary, recommended_ruling). Those blocks already contain the conclusions
the engine has to reach on its own (route_notification_sent, reroute_justified, the refund amount), so prepare() removes them before any rule
or engine sees the case: they score the ruling (ENT-ORGREF), they are never evidence. The ontology maps every field of every sample
(ontology.yaml disp001_mapping, disp003_mapping); this module is the code side of that mapping.
"""
from __future__ import annotations

import copy

REFERENCE_BLOCKS = ("case_metadata", "chat_log_analysis", "traffic_analysis", "evidence_summary", "recommended_ruling")


def prepare(case: dict) -> tuple[dict, dict]:
    """(case for the engines, the organizer's reference blocks). The input is not changed."""
    c = copy.deepcopy(case)
    reference = {k: c.pop(k) for k in REFERENCE_BLOCKS if k in c}
    logs = []
    for x in c.get("chat_logs") or []:
        y = dict(x)
        if "content" not in y and "message" in y:
            y["content"] = y["message"]                    # DISP-001 and DISP-003 write the text under "message"
        if "type" not in y:
            y["type"] = "message" if "content" in y else "other"      # a log entry without a type is a chat message
        y.setdefault("sender", "other")
        logs.append(y)
    if "chat_logs" in c:
        c["chat_logs"] = logs
    return c, reference


def reference_of(case: dict) -> dict:
    return prepare(case)[1]

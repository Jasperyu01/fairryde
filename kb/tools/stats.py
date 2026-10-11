"""Counts used in the gap analysis and the summary, computed from the YAML files and the check results."""
from __future__ import annotations

from collections import Counter


def compute(kb, rep, priv) -> dict:
    cred = Counter(r["credibility"] for r in kb.y["rules"]["rules"])
    mode = Counter(r["mode"] for r in kb.y["rules"]["rules"])
    q = Counter(x["status"] for x in rep.quotes)
    return {
        "n_rules": len(kb.rules),
        "n_cred_A": cred.get("A", 0), "n_cred_B": cred.get("B", 0), "n_cred_C": cred.get("C", 0), "n_cred_D": cred.get("D", 0),
        "n_mode_HARD": mode.get("HARD", 0), "n_mode_READ": mode.get("READ", 0), "n_mode_HR": mode.get("HARD+READ", 0),
        "n_quotes_verified": q.get("VERIFIED", 0), "n_quotes_bad": q.get("NOT_FOUND", 0) + q.get("NO_LOCAL_COPY", 0),
        "n_quotes_total": len(rep.quotes),
        "n_events": len(kb.y["ontology"]["events"]),
        "n_entities": len(kb.entities),
        "n_vocab": len(kb.vocab),
        "n_case_leaves": len(kb.case_leaves),
        "n_inventory": len(kb.y["inventory"]["items"]),
        "n_playbooks": len(kb.playbooks),
        "n_terms": rep.tables.get("term_sources_checked", 0),
        "n_priv_names": priv["before"]["PERSON_NAME"],
        "n_priv_tokens": priv["before"]["PERSON_NAME_TOKEN"],
        "n_priv_plates": priv["before"]["VEHICLE_PLATE"],
        "n_mapping": len(rep.tables.get("disp002_mapping", [])),
        "n_leaves": rep.tables.get("disp002_leaf_count", 0),
        "n_errors": rep.count("ERROR"), "n_warns": rep.count("WARN"),
    }


def fill(text: str, st: dict) -> str:
    out = str(text)
    for k, v in st.items():
        out = out.replace("{" + k + "}", str(v))
    return out

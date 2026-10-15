"""Pseudonymization before any cloud LLM call (CLAUDE.md, ChordX ONT.11, kb/privacy.yaml).

Names, vehicle plates, phone numbers and account IDs are replaced before text leaves the machine; places, dates, amounts and clause names stay.
The closed dictionary comes from the case's own structured fields (kb/tools/privacy_scan.py), so no mapping table is stored anywhere: the real
values exist only in the case file the app already holds. The same patterns run again as a boundary check on the exact strings that are sent
(leak_counts / assert_clean): a request that would carry an unredacted term is refused (PrivacyError), whichever mode runs.
Counts are reported, never the matched text.
"""
from __future__ import annotations

import re

from .kbaccess import privacy_scan as PS

ACCOUNT_ID = re.compile(r"\b[RD]-\d{3,6}\b")
SOURCE_ID = re.compile(r"\bRYDE-\d{6,}\b")        # a Ryde Help Centre article ID is public and 13 to 14 digits long; some pass the Luhn test by chance
# Name tokens that are also ordinary words in chat ("ok ah"): kept out of the token pass; the full name is always replaced.
TOKEN_STOPWORDS = {"ah", "la", "lah", "ya", "ok"}


class PrivacyError(RuntimeError):
    """Unredacted identifiers were found in text that was about to be sent to a cloud LLM."""


def build_terms(case: dict) -> list[tuple[str, str, str]]:
    """(term, code, type): names and name tokens, the plate, and the account IDs of the structured fields."""
    terms = [t for t in PS.dictionary(case) if not (t[2] == "PERSON_NAME_TOKEN" and t[0].lower() in TOKEN_STOPWORDS)]
    ids = {"RIDER-1": set(), "DRIVER-1": set()}
    ids["RIDER-1"] |= {v for v in (case.get("rider_profile", {}).get("rider_id"), case.get("trip_data", {}).get("rider_id"),
                                   case.get("dispute_ticket", {}).get("filed_by_id")) if v}
    ids["DRIVER-1"] |= {v for v in (case.get("driver_profile", {}).get("driver_id"), case.get("trip_data", {}).get("driver_id")) if v}
    for code, values in ids.items():
        terms += [(v, code, "ACCOUNT_ID") for v in sorted(values)]
    return terms


def pseudonymize(obj, terms):
    """A copy of any JSON-like object with every string pseudonymized (dictionary first, then patterns, then any leftover account ID)."""
    out = PS.pseudonymize(obj, terms)

    def walk(o):
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(v) for v in o]
        if isinstance(o, str):
            return ACCOUNT_ID.sub("ACCOUNT-X", o)
        return o
    return walk(out)


def leak_counts(strings, terms) -> dict:
    """Counts of dictionary terms and identifier patterns left in the strings (the runtime boundary check)."""
    counts = {"PERSON_NAME": 0, "PERSON_NAME_TOKEN": 0, "VEHICLE_PLATE": 0, "ACCOUNT_ID": 0, "ACCOUNT_ID_PATTERN": 0}
    counts.update({k: 0 for k in PS.PATTERNS})
    for s in strings:
        s = SOURCE_ID.sub("RYDE-ARTICLE", s)
        for term, _code, typ in terms:
            counts[typ] += len(re.findall(r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])", s, re.I))
        counts["ACCOUNT_ID_PATTERN"] += len(ACCOUNT_ID.findall(s))
        for k, p in PS.PATTERNS.items():
            hits = p.findall(s)
            if k == "LONG_NUMBER":
                hits = [h for h in hits if PS._luhn(h)]
            counts[k] += len(hits)
    counts["total"] = sum(counts.values())
    return counts


def assert_clean(strings, terms) -> dict:
    counts = leak_counts(strings, terms)
    if counts["total"]:
        raise PrivacyError(f"request blocked: unredacted identifiers found (counts only): { {k: v for k, v in counts.items() if v and k != 'total'} }")
    return counts

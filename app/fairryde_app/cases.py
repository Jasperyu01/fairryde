"""The cases the app can run, and what each is expected to give.

- organizer cases: DISP-001 to DISP-003, read from kb/sources/organizer through the KB loader. The organizer's own answer blocks are
  removed later by case_adapter.prepare() (ENT-ORGREF); expected values come from kb/organizer_cases.yaml.
- validation cases: E01 to E15 in validation/V4_e2e/cases. Expected outcome and amount come from the settled references
  (validation/V4_e2e/42_reference.jsonl). Expected tier: the tier of the A6 engine rerun (validation/build_checks/A6/01_engine_rerun.json),
  and HUMAN for a case the settled reference says a person must decide.
- demo case: DEMO-SAFETY-01 (app/sample_cases), a synthetic safety case for the Section 5 path. It has no expected values.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache

from . import config
from .kbaccess import get_kb


@dataclass
class CaseInfo:
    case_id: str
    kind: str                      # organizer | validation | demo
    dispute_type: str
    title: str
    expected: dict = field(default_factory=dict)       # outcome, amount_sgd, tier, source
    profile_override: str | None = None


def _validation_reference() -> dict:
    out = {}
    path = config.VALIDATION_DIR / "V4_e2e" / "42_reference.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            out[d["case_id"]] = d
    return out


def _engine_rerun_tiers() -> dict:
    path = config.VALIDATION_DIR / "build_checks" / "A6" / "01_engine_rerun.json"
    return {x["case_id"]: x["tier"] for x in json.loads(path.read_text(encoding="utf-8"))}


@lru_cache(maxsize=1)
def _catalog() -> dict[str, CaseInfo]:
    kb = get_kb()
    cat: dict[str, CaseInfo] = {}
    for cid, case in kb.organizer_cases.items():
        e = kb.expected[cid]
        cat[cid] = CaseInfo(cid, "organizer", case["dispute_ticket"]["dispute_type"], f"{cid} ({e['dispute_type']}), organizer sample",
                            {"outcome": e["expected_outcome"], "amount_sgd": e.get("expected_amount_sgd"), "tier": e["expected_tier"],
                             "source": "kb/organizer_cases.yaml"})
    ref, tiers = _validation_reference(), _engine_rerun_tiers()
    for path in sorted(config.VALIDATION_CASES_DIR.glob("E*.json")):
        cid = path.stem
        case = json.loads(path.read_text(encoding="utf-8"))
        r = ref.get(cid, {})
        human = bool(r.get("labeler", {}).get("human"))
        tier = "HUMAN" if human else tiers.get(cid)
        cat[cid] = CaseInfo(cid, "validation", case["dispute_ticket"]["dispute_type"], f"{cid} ({case['dispute_ticket']['dispute_type']}), validation case",
                            {"outcome": r.get("reference_outcome"), "amount_sgd": r.get("reference_amount"), "tier": tier,
                             "source": "validation/V4_e2e/42_reference.jsonl" + (", build_checks/A6/01_engine_rerun.json" if cid in tiers else "")
                             + (" (reference: a person decides)" if human else "")})
    for path in sorted(config.SAMPLE_CASES_DIR.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        cid = case["dispute_ticket"]["dispute_id"]
        cat[cid] = CaseInfo(cid, "demo", case["dispute_ticket"]["dispute_type"], f"{cid} (synthetic safety demo)",
                            {"outcome": "ESCALATE_HUMAN", "amount_sgd": None, "tier": "HUMAN", "source": "design (policy v2.1 Section 5.2)"},
                            profile_override=case.get("_app_profile"))
    return cat


def list_cases() -> list[CaseInfo]:
    return list(_catalog().values())


def get_info(case_id: str) -> CaseInfo:
    try:
        return _catalog()[case_id]
    except KeyError:
        raise KeyError(f"unknown case {case_id!r}; known: {', '.join(_catalog())}") from None


def load_case(case_id: str) -> dict:
    """The case file as the source gives it (a fresh copy; the organizer's answer blocks are still in it, case_adapter.prepare removes them)."""
    info = get_info(case_id)
    if info.kind == "organizer":
        return json.loads(json.dumps(get_kb().organizer_cases[case_id]))
    if info.kind == "validation":
        return json.loads((config.VALIDATION_CASES_DIR / f"{case_id}.json").read_text(encoding="utf-8"))
    for path in config.SAMPLE_CASES_DIR.glob("*.json"):
        case = json.loads(path.read_text(encoding="utf-8"))
        if case["dispute_ticket"]["dispute_id"] == case_id:
            return case
    raise KeyError(case_id)

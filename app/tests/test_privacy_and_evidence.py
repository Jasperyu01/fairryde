"""Privacy boundary (names, plates, phones, account IDs never reach an LLM; the organizer's answer never reaches an agent) and the evidence IDs."""
import json
import re

import pytest

from conftest import SpyClient
from fairryde_app import cases, evidence as ev, intake, pipeline, privacy
from fairryde_app.kbaccess import P21, case_adapter, engine_noshow, get_kb, privacy_scan as PS

ALL_CASES = [i.case_id for i in cases.list_cases()]


@pytest.mark.parametrize("case_id", ALL_CASES)
def test_no_identifier_leaves_the_machine(case_id):
    raw = cases.load_case(case_id)
    canon, ref = case_adapter.prepare(raw)
    spy = SpyClient()
    pipeline.run_case(case_id, client=spy, save=False)
    assert spy.requests
    text = "\n".join("\n".join(q["system"]) + "\n" + q["user"] for q in spy.requests)
    for term, code, typ in privacy.build_terms(canon):
        if typ == "PERSON_NAME_TOKEN" and len(term) < 3:
            continue
        assert not re.search(r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])", text, re.I), f"{case_id}: {typ} {code} found in a request"
    assert privacy.leak_counts([text], privacy.build_terms(canon))["total"] == 0
    assert not re.search(r"\bS[A-Z]{1,2}\s?\d{1,4}\s?[A-Z]\b", text)                  # no Singapore plate
    assert not re.search(r"\b[RD]-\d{3,6}\b", text)                                    # no account ID
    assert not re.search(r"\b[3689]\d{3}[\s-]?\d{4}\b", text)                          # no phone number


@pytest.mark.parametrize("case_id", ["DISP-001", "DISP-002", "DISP-003"])
def test_the_organizers_own_answer_never_reaches_an_agent(case_id):
    raw = cases.load_case(case_id)
    _canon, ref = case_adapter.prepare(raw)
    spy = SpyClient()
    pipeline.run_case(case_id, client=spy, save=False)
    text = "\n".join(q["user"] for q in spy.requests)
    strings = []

    def walk(o):
        if isinstance(o, dict):
            [walk(v) for v in o.values()]
        elif isinstance(o, list):
            [walk(v) for v in o]
        elif isinstance(o, str) and len(o) >= 40:
            strings.append(o)
    walk(ref)
    own = json.dumps([i["data"] for i in ev.extract(get_kb(), _canon)], ensure_ascii=False)       # a quote of a chat message is also the chat message
    for s in strings:
        if s in own:
            continue
        assert s not in text, f"{case_id}: a sentence of the organizer's reference blocks reached an agent: {s[:60]}"
    for key in ("recommended_ruling", "chat_log_analysis", "traffic_analysis", "evidence_summary", "case_metadata", "root_cause", "route_deviated"):
        assert key not in text


def test_a_leaking_request_is_blocked_before_it_is_sent():
    kb = get_kb()
    raw = cases.load_case("DISP-002")
    canon, _ = case_adapter.prepare(raw)
    terms = privacy.build_terms(canon)
    name = PS.dictionary(canon)[0][0]
    with pytest.raises(privacy.PrivacyError):
        privacy.assert_clean([f"hello {name}, your plate is SGP 4521 M and number 9123 4567"], terms)
    assert privacy.assert_clean(["hello RIDER-NAME-1"], terms)["total"] == 0


def test_a_blocked_run_never_calls_the_client(monkeypatch):
    spy = SpyClient()
    from fairryde_app import agents
    monkeypatch.setattr(agents, "policy_context", lambda *a, **k: "Policy. The driver is Lim Wei Ming.")
    from fairryde_app import pipeline as pl
    monkeypatch.setattr(pl.agents, "policy_context", lambda *a, **k: "Policy. The driver is Lim Wei Ming.")
    with pytest.raises(privacy.PrivacyError):
        pl.run_case("DISP-002", client=spy, save=False)
    assert spy.requests == []


def test_run_logs_hold_only_the_pseudonymized_view(tmp_path):
    raw = cases.load_case("DISP-002")
    canon, _ = case_adapter.prepare(raw)
    run = pipeline.run_case("DISP-002", mode="mock", save=True, runs_dir=tmp_path)
    log = open(run["log_file"], encoding="utf-8").read()
    for term, code, typ in privacy.build_terms(canon):
        if typ in ("PERSON_NAME", "VEHICLE_PLATE", "ACCOUNT_ID") or (typ == "PERSON_NAME_TOKEN" and len(term) > 3):
            assert not re.search(r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])", log, re.I), (typ, code)


# ------------------------------------------------------------------ evidence
SUPPORTED = ["DISP-001", "DISP-002", "DISP-003", "E01", "E02", "E03", "E04", "E11"]


def _items(case_id):
    kb = get_kb()
    canon, _ = case_adapter.prepare(cases.load_case(case_id))
    return kb, canon, ev.extract(kb, canon)


@pytest.mark.parametrize("case_id", ["DISP-002", "E01", "E02", "E03", "E04"])
def test_ids_cover_the_no_show_engines_index(case_id):
    kb, canon, items = _items(case_id)
    assert set(engine_noshow.evidence_index(canon, kb)) <= {i["id"] for i in items}


@pytest.mark.parametrize("case_id", ["DISP-001", "DISP-003"])
def test_ids_cover_the_route_and_surge_index(case_id):
    kb, canon, items = _items(case_id)
    assert set(P21.evidence_index(canon)) <= {i["id"] for i in items}


@pytest.mark.parametrize("case_id", SUPPORTED)
def test_every_evidence_id_an_engine_cites_exists(case_id):
    from fairryde_app import engine_stage
    kb, canon, items = _items(case_id)
    raw = cases.load_case(case_id)
    cls = intake.classify(kb, raw, case_id)
    out = engine_stage.run_engine(kb, raw, cls, canon)
    ids = {i["id"] for i in items}
    cited = {b.split(".")[0] for f in out["findings"].values() for b in f.get("basis") or [] if b.startswith("E-") and "*" not in b}
    cited |= {b.split(".")[0] for s in out["steps"] for b in s.get("evidence") or [] if b.startswith("E-") and "*" not in b}
    assert cited <= ids, sorted(cited - ids)


@pytest.mark.parametrize("case_id", ALL_CASES)
def test_evidence_has_no_coordinates_no_profile_and_no_organizer_conclusions(case_id):
    _kb, _canon, items = _items(case_id)
    text = json.dumps([i["data"] for i in items])
    assert '"lat"' not in text and '"lng"' not in text
    for key in ("root_cause", "route_deviated", "recommended_ruling", "fraud_flags", "dispute_history", "avg_rating"):
        assert key not in text
    withheld = {i["id"] for i in items if i["withheld"]}
    assert withheld == {"E-PRF-R", "E-PRF-D"}
    assert all(not i["data"] for i in items if i["withheld"])
    view = {v["id"]: v for v in ev.agent_view(items)}
    assert all("data" not in view[w] for w in withheld)


def test_ids_are_stable_and_unique():
    _kb, _canon, a = _items("DISP-001")
    _kb, _canon, b = _items("DISP-001")
    assert [i["id"] for i in a] == [i["id"] for i in b] and len({i["id"] for i in a}) == len(a)


HISTORY = re.compile(r"fraud|FRD-|past disputes|dispute_history|flagged_for|avg_rating|total_trips|account_age|platform flag", re.I)


@pytest.mark.parametrize("case_id", ALL_CASES)
def test_agents_are_history_blind(case_id):
    """GEN-R03: no agent sees account history, a fraud signal or its detail (only the deterministic Section 6 threshold reaches the Judge, without its reason)."""
    spy = SpyClient()
    pipeline.run_case(case_id, client=spy, save=False)
    for q in spy.requests:
        assert not HISTORY.search(q["user"]), (case_id, q["agent"], HISTORY.findall(q["user"]))

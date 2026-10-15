"""Every saved response set passes the same verifier as a live answer, and every case runs offline."""
import pytest

from conftest import run_mock
from fairryde_app import cases, config, llm


@pytest.mark.parametrize("case_id", [i.case_id for i in cases.list_cases()])
def test_every_case_runs_offline_and_every_ruling_fixture_verifies(case_id):
    run = run_mock(case_id)
    r = run["result"]
    assert r["tier"] in ("AUTO", "APPROVE", "HUMAN")
    if r["status"] != "CASE_FILE":
        assert r["gate"] is None, (case_id, r["tier_reasons"])
        assert all(c["status"] != "FAIL" for v in run["verification"]["judge"] for c in v["checks"])
    else:
        assert r["outcome"] == "ESCALATE_HUMAN" and r["amount_sgd"] is None and r["tier"] == "HUMAN"


@pytest.mark.parametrize("scenario", list(llm.MOCK_SCENARIOS))
def test_every_scenario_runs(scenario):
    run = run_mock("DISP-001", scenario)
    assert run["scenario"] == scenario and run["result"]["tier"] in ("APPROVE", "HUMAN")


def test_a_case_without_a_fixture_is_reported_not_guessed(tmp_path):
    client = llm.MockClient(mock_dir=tmp_path)
    with pytest.raises(llm.MockMissing):
        client.complete(agent="judge", case_id="DISP-001")


def test_fixtures_are_marked_as_authored_unless_recorded():
    import json
    for p in config.MOCK_DIR.glob("*.json"):
        fx = json.loads(p.read_text(encoding="utf-8"))
        assert fx["source"] in ("hand-written", "composed from the deterministic stages", "recorded from a live run"), p.name

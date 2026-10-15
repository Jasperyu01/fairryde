"""The required cases, end to end in mock mode: outcome, amount and tier against what is expected."""
import json

import pytest

from conftest import REQUIRED_CASES, run_mock
from fairryde_app import cases, pipeline

# The task's own expectations for the three organizer samples (also in kb/organizer_cases.yaml).
SPEC = {"DISP-001": ("PARTIAL_REFUND", 3.44, "APPROVE"), "DISP-002": ("UPHOLD", None, "APPROVE"), "DISP-003": ("FULL_REFUND", 4.50, "AUTO")}


@pytest.mark.parametrize("case_id", REQUIRED_CASES)
def test_case_matches_expected(case_id):
    run = run_mock(case_id)
    exp = cases.get_info(case_id).expected
    r = run["result"]
    assert r["outcome"] == exp["outcome"], (case_id, r["outcome"], exp)
    if exp["amount_sgd"] is None:
        assert r["amount_sgd"] in (None, 0, 0.0)
    else:
        assert r["amount_sgd"] == pytest.approx(exp["amount_sgd"], abs=0.005)
    assert r["tier"] == exp["tier"], (case_id, r["tier"], r["tier_reasons"])
    assert run["expected_check"]["ok"]
    assert r["gate"] in (None, "GEN-R07")                    # no verification gate fired on a normal replay


@pytest.mark.parametrize("case_id,spec", SPEC.items())
def test_organizer_samples_as_the_task_states(case_id, spec):
    r = run_mock(case_id)["result"]
    assert (r["outcome"], r["amount_sgd"], r["tier"]) == (spec[0], spec[1], spec[2]) or (r["amount_sgd"] is None and spec[1] is None and r["outcome"] == spec[0] and r["tier"] == spec[2])


def test_disp001_tier_is_approve_because_of_4_3_km():
    run = run_mock("DISP-001")
    assert run["engine"]["deviation_km"] == pytest.approx(4.3)
    assert any("4.3 km" in t and "2.0 km" in t for t in run["result"]["tier_reasons"])


def test_disp002_tier_is_approve_because_of_the_fraud_flag_but_agents_never_see_it():
    run = run_mock("DISP-002")
    r = run["result"]
    assert r["tier"] == "APPROVE" and r["section6"]["threshold"] == 0.95
    assert run["engine"]["fraud_flags"] == 1
    blob = json.dumps([m["json"] for m in run["messages"]] + [r["rider_explanation"], r["driver_explanation"]]).lower()
    assert "fraud" not in blob


def test_disp003_is_final_under_10_dollars():
    r = run_mock("DISP-003")["result"]
    assert r["status"] == "FINAL" and r["tier"] == "AUTO" and r["case_file"] is None and not r["escalation"]["required"]


def test_every_ruling_cites_only_existing_ids_and_the_amount_equals_the_engine():
    for case_id in REQUIRED_CASES:
        run = run_mock(case_id)
        if run["result"]["status"] == "CASE_FILE":
            continue
        assert all(c["status"] != "FAIL" for v in run["verification"]["judge"] for c in v["checks"]), case_id
        assert run["result"]["amount_sgd"] == run["engine"]["amount_sgd"]


def test_run_log_is_written_as_json(tmp_path):
    run = pipeline.run_case("DISP-003", mode="mock", save=True, runs_dir=tmp_path)
    log = json.loads(open(run["log_file"], encoding="utf-8").read())
    assert log["case_id"] == "DISP-003" and log["result"]["outcome"] == "FULL_REFUND" and log["mode"] == "mock"
    assert {e["type"] for e in log["events"]} >= {"stage", "message", "verification", "final"}
    assert [m["agent"] for m in log["messages"]] == ["rider_advocate", "driver_advocate", "judge"]


def test_e10_has_no_engine_and_escalates_under_gen_r07():
    run = run_mock("E10")
    assert run["engine"]["engine"] == "none" and run["result"]["tier"] == "HUMAN" and run["result"]["outcome"] == "ESCALATE_HUMAN"
    assert "FC-R00" in run["engine"]["rules"] and run["result"]["amount_sgd"] is None

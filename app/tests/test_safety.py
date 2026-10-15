"""Policy v2.1 Section 5: on a safety case the agents prepare a case file only, with no ruling and no recommendation."""
import json

import pytest

from conftest import SpyClient, run_mock
from fairryde_app import pipeline, safety


@pytest.mark.parametrize("case_id", ["DEMO-SAFETY-01", "E13"])
def test_safety_case_is_a_case_file_with_no_ruling(case_id):
    run = run_mock(case_id)
    r = run["result"]
    assert r["status"] == "CASE_FILE" and r["case_file_only"]
    assert (r["outcome"], r["amount_sgd"], r["payer"], r["payee"], r["tier"]) == ("ESCALATE_HUMAN", None, None, None, "HUMAN")
    assert r["reasons"] == ["SE-R-HUMAN-DECIDES"] and r["gate"] == "G4"
    assert r["case_file"] is not None and r["escalation"]["required"]
    assert all(m["mode"] == "case_file" for m in run["messages"])


def test_safety_agents_write_no_ruling_or_recommendation():
    run = run_mock("DEMO-SAFETY-01")
    for m in run["messages"]:
        assert safety.lint(json.dumps(m.get("json_shown") or m["json"])) == [], m["agent"]
    assert "recommend" not in (run["result"]["rider_explanation"] + run["result"]["driver_explanation"]).lower()


def test_the_judge_of_a_safety_case_is_not_told_the_engine_verdict_or_amount():
    spy = SpyClient()
    pipeline.run_case("DEMO-SAFETY-01", client=spy, save=False)
    judge = next(q for q in spy.requests if q["agent"] == "judge")
    payload = json.loads(judge["user"].split("<case_file>")[1].split("</case_file>")[0])
    assert payload["mode"] == "case_file" and "amount_sgd" not in payload["engine_result"] and "outcome" not in payload["engine_result"]
    assert "Section 5.2" in judge["system"][0]


def test_a_ruling_or_recommendation_in_agent_text_is_removed():
    def tamper(agent, mode, attempt, data):
        if agent == "judge" and mode == "case_file":
            data["case_summary"] = "The driver is at fault and should be suspended. The rider should be refunded S$4.50. The records show a message at 21:18:50 [E-CHT-04]."
        if agent == "driver_advocate":
            data["account_summary"] = "I recommend that the driver keep the fare. The driver says nothing about the exchange [E-CHT-04]."
    run = pipeline.run_case("DEMO-SAFETY-01", client=SpyClient(tamper=tamper), save=False)
    shown = json.dumps([m.get("json_shown") for m in run["messages"]])
    assert "at fault" not in shown and "should be suspended" not in shown and "I recommend" not in shown
    assert safety.REDACTED in shown and "[E-CHT-04]" in shown                       # the factual sentence stays
    assert any(c["kind"] == "safety" for v in run["verification"]["judge"] for c in v["checks"])
    assert run["result"]["outcome"] == "ESCALATE_HUMAN"


def test_the_judge_notices_safety_content_the_keywords_missed():
    run = run_mock("DISP-003", "late_safety_flag")
    r = run["result"]
    assert (r["status"], r["outcome"], r["amount_sgd"], r["tier"], r["gate"]) == ("CASE_FILE", "ESCALATE_HUMAN", None, "HUMAN", "G4")
    assert [m["mode"] for m in run["messages"] if m["agent"] == "judge"] == ["ruling", "case_file"]
    assert "ruling was withdrawn" in r["tier_reasons"][0]


def test_an_advocate_notices_safety_content_the_keywords_missed():
    def tamper(agent, mode, attempt, data):
        if agent == "rider_advocate" and mode == "ruling":
            data["safety_concern"] = True
    run = pipeline.run_case("DISP-003", client=SpyClient(tamper=tamper), save=False)
    assert run["result"]["status"] == "CASE_FILE" and run["result"]["tier"] == "HUMAN" and run["result"]["amount_sgd"] is None
    assert any(e["type"] == "notice" for e in run["events"])


def test_no_engine_case_is_a_case_file_under_gen_r07():
    for case_id in ("E05", "E12"):
        r = run_mock(case_id)["result"]
        assert (r["status"], r["outcome"], r["tier"], r["gate"]) == ("CASE_FILE", "ESCALATE_HUMAN", "HUMAN", "GEN-R07") and r["reasons"] == ["GEN-R-POLICY-GAP"]


@pytest.mark.parametrize("text,flagged", [
    ("The rider says the driver shouted at them [E-TKT-01].", False),
    ("The record shows a message at 21:18:50.", False),
    ("The driver is at fault.", True),
    ("I recommend that the account be suspended.", True),
    ("The rider should be refunded.", True),
    ("The driver should have stopped.", True),
    ("A refund is warranted.", True),
    ("No outcome, amount or measure is proposed.", False),
])
def test_lint(text, flagged):
    assert bool(safety.lint(text)) is flagged

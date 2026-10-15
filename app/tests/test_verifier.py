"""The verifier: every cited ID must exist, amounts must equal the engine's, and a disagreement or a low confidence escalates."""
import copy
import json

import pytest

from conftest import SpyClient, run_mock
from fairryde_app import cases, engine_stage, evidence as ev, intake, llm, mockgen, pipeline, tiering, verifier
from fairryde_app.agents import policy_context
from fairryde_app.kbaccess import case_adapter, get_kb


@pytest.fixture(scope="module")
def disp001():
    kb = get_kb()
    raw = cases.load_case("DISP-001")
    cls = intake.classify(kb, raw, "DISP-001")
    canon, _ = case_adapter.prepare(raw)
    items = ev.extract(kb, canon)
    out = engine_stage.run_engine(kb, raw, cls, canon)
    ctx = verifier.build_context(kb, cls.profile, items, out, policy_context(kb, cls.profile, out, cls))
    good = mockgen.disp001()["judge"]
    return ctx, good


def check(ctx, j):
    return verifier.verify_judge(ctx, j)


def test_the_saved_judge_answer_passes(disp001):
    ctx, good = disp001
    r = check(ctx, good)
    assert r["ok"], [c for c in r["checks"] if c["status"] == "FAIL"]


@pytest.mark.parametrize("field,bad,needle", [
    ("evidence", ["E-TRP-01", "E-XYZ-99"], "E-XYZ-99"),
    ("evidence", ["E-PRF-R"], "withheld"),
    ("rules", ["FC-R99"], "FC-R99"),
    ("policy_sections", ["Section 9.9"], "Section 9.9"),
    ("precedents", ["Precedent 8.1"], "Precedent 8.1"),
])
def test_unknown_citation_fails_and_can_be_retried(disp001, field, bad, needle):
    ctx, good = disp001
    j = copy.deepcopy(good)
    j[field] = bad
    r = check(ctx, j)
    assert not r["ok"] and r["retryable_failure"] and needle in r["feedback"]


def test_an_unknown_id_hidden_in_the_prose_is_found(disp001):
    ctx, good = disp001
    j = copy.deepcopy(good)
    j["reasoning"] += " See also [E-GPS-99] and rule FC-R77 and Section 12.4."
    r = check(ctx, j)
    assert not r["ok"]
    assert "E-GPS-99" in r["feedback"] and "FC-R77" in r["feedback"] and "Section 12.4" in r["feedback"]


@pytest.mark.parametrize("change,needle", [({"amount_sgd": 6.5}, "amount"), ({"outcome": "FULL_REFUND"}, "outcome"), ({"payer": "DRIVER"}, "payer"), ({"outcome": "UPHOLD", "amount_sgd": None}, "outcome")])
def test_disagreement_with_the_engine_is_detected(disp001, change, needle):
    ctx, good = disp001
    j = {**copy.deepcopy(good), **change}
    r = check(ctx, j)
    assert r["disagrees"] and not r["retryable_failure"] and any(needle in d for d in r["engine_diffs"])


def test_an_amount_within_a_cent_tolerance_agrees(disp001):
    ctx, good = disp001
    assert not check(ctx, {**good, "amount_sgd": 3.444})["disagrees"]


def test_a_number_that_is_not_in_the_case_fails_the_explanation(disp001):
    ctx, good = disp001
    j = {**copy.deepcopy(good), "rider_explanation": good["rider_explanation"] + " You also receive a goodwill credit of S$7.80."}
    r = check(ctx, j)
    assert not r["ok"] and "7.80" in r["feedback"]


def test_a_number_followed_by_a_comma_is_not_a_new_number(disp001):
    ctx, good = disp001
    assert verifier.numbers_unmatched("The trip ended at 13:52, and the fare was S$35.00, as quoted.", ctx.allowed_numbers, ctx.quotes) == []


@pytest.mark.parametrize("text", ["RIDER-NAME-1 should know this.", "A fraud flag was raised.", ""])
def test_party_text_rules(disp001, text):
    ctx, good = disp001
    r = check(ctx, {**good, "driver_explanation": text})
    assert not r["ok"]


def test_schema_errors(disp001):
    ctx, good = disp001
    assert not check(ctx, {k: v for k, v in good.items() if k != "confidence"})["ok"]
    assert not check(ctx, {**good, "confidence": 1.7})["ok"]
    assert not check(ctx, {**good, "outcome": "MAYBE"})["ok"]


def test_the_confidence_is_the_lower_of_judge_and_engine():
    c = tiering.final_confidence(0.9, {"confidence": {"C": 1.0, "C_effective": 0.839}})
    assert c["final"] == 0.839
    assert tiering.final_confidence(0.7, {"confidence": {"C": 1.0, "C_effective": 1.0}})["final"] == 0.7


# ------------------------------------------------------------------ the pipeline's reaction
def test_judge_disagreement_escalates_to_a_human_with_the_full_case_file():
    run = run_mock("DISP-001", "judge_disagrees")
    r = run["result"]
    assert (r["gate"], r["outcome"], r["tier"], r["amount_sgd"]) == ("G8", "ESCALATE_HUMAN", "HUMAN", None)
    assert r["reasons"] == ["GEN-R-ESCALATED"]
    cf = r["case_file"]
    assert cf["engine_ruling"]["outcome"] == "PARTIAL_REFUND" and cf["judge_ruling"]["outcome"] == "UPHOLD"
    assert cf["evidence"] and cf["rider_advocate_brief"] and cf["driver_advocate_brief"] and cf["verification"]


def test_citation_error_is_retried_once_then_accepted():
    run = run_mock("DISP-001", "bad_citation_fixed")
    judge_msgs = [m for m in run["messages"] if m["agent"] == "judge"]
    assert len(judge_msgs) == 2 and judge_msgs[1]["attempt"] == 1
    assert run["verification"]["judge"][0]["ok"] is False and run["verification"]["judge"][1]["ok"] is True
    assert run["result"]["gate"] is None and run["result"]["outcome"] == "PARTIAL_REFUND" and run["result"]["explanation_source"] == "judge"


def test_citation_error_after_the_retry_is_gate_g7_with_the_engines_ruling_for_approval():
    run = run_mock("DISP-003", "bad_citation")
    r = run["result"]
    assert [m["attempt"] for m in run["messages"] if m["agent"] == "judge"] == [0, 1]
    assert (r["gate"], r["tier"], r["outcome"], r["amount_sgd"]) == ("G7", "APPROVE", "FULL_REFUND", 4.5)       # AUTO would have been the tier; G7 keeps it for approval
    assert r["explanation_source"] == "engine_draft" and r["case_file"] is not None


def test_the_retry_request_carries_the_verifier_feedback():
    spy = SpyClient("bad_citation_fixed")
    pipeline.run_case("DISP-001", client=spy, save=False)
    judge_reqs = [q for q in spy.requests if q["agent"] == "judge"]
    assert len(judge_reqs) == 2 and "verifier_feedback" not in judge_reqs[0]["user"] and "E-XYZ-99" in judge_reqs[1]["user"] and "verifier_feedback" in judge_reqs[1]["user"]


def test_low_confidence_below_the_threshold_escalates_a_ruling_that_would_be_automatic():
    # E04 (profile organizer_case) is AUTO at the engine; a Judge confidence of 0.55 is below TAU 0.6 (AUTH-01)
    base = run_mock("E04")["result"]
    low = run_mock("E04", "low_confidence")["result"]
    assert base["tier"] == "AUTO" and low["tier"] == "APPROVE"
    assert low["escalation"]["required"] and low["case_file"] is not None and any("below" in t for t in low["tier_reasons"])
    assert (low["outcome"], low["amount_sgd"]) == (base["outcome"], base["amount_sgd"])       # the ruling stays as the recommended remedy


def test_low_confidence_in_policy_v21_uses_the_section_6_threshold():
    r = run_mock("DISP-001", "low_confidence")["result"]
    assert r["tier"] == "APPROVE" and r["confidence"]["final"] == 0.55 and r["confidence"]["below_threshold"] and r["confidence"]["threshold"] == 0.8


def test_section6_unit_rules():
    kb = get_kb()
    base = {"profile": "organizer_v2_1", "claim_type": "FC-ROUTE", "amount_at_stake": 20.0, "fraud_flags": 0, "deviation_km": 1.5, "engine_tier": "AUTO", "triggers": [],
            "confidence": {"C": 1.0, "C_effective": 1.0}}
    assert tiering.tier_for_ruling(kb, base, 0.9, "AUTO")["tier"] == "AUTO"                          # S$10 to S$50, 80% met, deviation under 2 km
    assert tiering.tier_for_ruling(kb, base, 0.7, "AUTO")["tier"] == "APPROVE"                       # confidence under 80%
    assert tiering.tier_for_ruling(kb, {**base, "amount_at_stake": 60.0}, 0.99, "AUTO")["tier"] == "HUMAN"      # above S$50: always human review
    assert tiering.tier_for_ruling(kb, {**base, "fraud_flags": 1}, 0.9, "AUTO")["tier"] == "APPROVE"            # Section 6.3: 95%
    assert tiering.tier_for_ruling(kb, {**base, "claim_type": "FC-SURGE", "amount_at_stake": 4.5, "deviation_km": None}, 0.3, "AUTO")["tier"] == "AUTO"     # under S$10 any confidence
    assert tiering.tier_for_ruling(kb, base, 0.99, "HUMAN")["tier"] == "HUMAN"                       # a Judge may be stricter, never looser
    assert tiering.tier_for_ruling(kb, {**base, "engine_tier": "APPROVE"}, 0.99, "AUTO")["tier"] == "APPROVE"


def test_advocate_citations_that_do_not_exist_are_removed_before_the_judge_reads_them():
    def tamper(agent, mode, attempt, data):
        if agent == "rider_advocate":
            data["arguments"][0]["evidence"] = data["arguments"][0]["evidence"] + ["E-ZZZ-01", "E-PRF-R"]
            data["arguments"][0]["rules"] = ["FC-R99"]
    spy = SpyClient(tamper=tamper)
    run = pipeline.run_case("DISP-001", client=spy, save=False)
    assert run["verification"]["rider_advocate"]["ok"] is False
    assert set(run["verification"]["rider_advocate"]["invalid"]["evidence"]) == {"E-ZZZ-01"} and run["verification"]["rider_advocate"]["invalid"]["withheld"] == ["E-PRF-R"]
    judge_req = next(q for q in spy.requests if q["agent"] == "judge")["user"]
    brief = json.loads(judge_req.split("<case_file>")[1].split("</case_file>")[0])["briefs"]["rider_advocate"]
    assert "E-ZZZ-01" not in json.dumps(brief["arguments"]) and "FC-R99" not in json.dumps(brief["arguments"])
    assert run["result"]["outcome"] == "PARTIAL_REFUND"           # a bad advocate citation does not change the ruling

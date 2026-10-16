"""New input on the public app: an edited complaint and an uploaded case run on a copy, under the right profile, with no reference ruling and
the same privacy boundary; a file that does not fit is refused with a clear message; live mode follows the access code and the run cap."""
import json

import pytest

from conftest import SpyClient
from fairryde_app import cases, pipeline, privacy, userinput as U
from fairryde_app.kbaccess import case_adapter


class FakeLive(SpyClient):
    """Stands in for the live client: keeps every request and replays the saved answers of a listed case, whatever the run's case id."""
    name = "live"

    def __init__(self, base):
        super().__init__()
        self.base = base

    def complete(self, *, case_id, **kw):
        return super().complete(case_id=self.base, **kw)


def first_name_term(raw):
    canon, _ = case_adapter.prepare(raw)
    term, code, _typ = next(t for t in privacy.build_terms(canon) if t[2] == "PERSON_NAME")
    return term, code


def test_an_edited_complaint_runs_on_a_copy_under_the_same_profile_with_no_reference_ruling():
    text = "The driver went a long way round through Geylang and never said why. I want my money back."
    cid, raw, profile = U.edited_case("DISP-001", text)
    assert (cid, profile) == ("DISP-001-EDITED", "organizer_v2_1")
    assert U.complaint_of(cases.load_case("DISP-001")) != text                    # the listed case is not changed
    fake = FakeLive("DISP-001")
    run = pipeline.run_case(cid, client=fake, raw_case=raw, profile=profile, input_label=U.EDITED_LABEL, save=False)
    assert run["mode"] == "live" and run["classification"]["profile"] == "organizer_v2_1" and run["engine"]["engine"] == "engine_route"
    assert run["input_label"] == "edited case, no reference ruling" and run["expected"] is None and run["expected_check"] is None
    assert any(text in r["user"] for r in fake.requests)                          # the agents read the new text
    assert run["result"]["tier"] in ("AUTO", "APPROVE", "HUMAN")


def test_an_edited_regression_case_keeps_its_own_profile():
    cid, raw, profile = U.edited_case("E01", "The driver cancelled and charged me a fee although I was at the pick-up point.")
    assert profile == "ryde_2026"
    assert pipeline.run_stages(cid, raw, profile=profile)["classification"]["profile"] == "ryde_2026"


def test_a_name_typed_into_an_edited_complaint_is_pseudonymized_before_the_model_call():
    name, code = first_name_term(cases.load_case("DISP-002"))
    cid, raw, profile = U.edited_case("DISP-002", f"My name is {name} and I was waiting at the venue, not at the pin.")
    fake = FakeLive("DISP-002")
    pipeline.run_case(cid, client=fake, raw_case=raw, profile=profile, input_label=U.EDITED_LABEL, save=False)
    assert fake.requests and not any(name.lower() in (r["user"] + " ".join(r["system"])).lower() for r in fake.requests)
    assert any(code in r["user"] for r in fake.requests)


def test_the_example_upload_is_built_from_our_own_sample_and_is_a_valid_case():
    ex = U.example_upload()
    demo = cases.load_case("DEMO-SAFETY-01")
    assert ex["trip_data"] == demo["trip_data"] and ex["dispute_ticket"]["dispute_id"] == U.EXAMPLE_ID and not [k for k in ex if k.startswith("_")]
    cid, raw = U.parse_upload(json.dumps(ex).encode())
    run = pipeline.run_stages(cid, raw, profile="organizer_v2_1")
    assert cid == U.EXAMPLE_ID and not run["classification"]["safety"]["flag"]
    assert (run["engine"]["engine"], run["engine"]["outcome"], run["engine"]["amount_sgd"]) == ("engine_surge", "FULL_REFUND", 4.5)


def test_an_uploaded_case_runs_under_organizer_v2_1_with_no_reference_ruling_and_pseudonymized():
    ex = U.example_upload()
    name, code = first_name_term(ex)
    ex["dispute_ticket"]["dispute_id"] = "MY-CASE-7"                             # not a DISP-nnn id: META-01 alone would pick ryde_2026
    ex["dispute_ticket"]["description"] = f"I am {name}. " + ex["dispute_ticket"]["description"]
    cid, raw = U.parse_upload(json.dumps(ex).encode())
    fake = FakeLive("DISP-003")
    run = pipeline.run_case(cid, client=fake, raw_case=raw, profile="organizer_v2_1", input_label=U.UPLOADED_LABEL, save=False)
    assert cid == "UPLOAD-MY-CASE-7" and run["classification"]["profile"] == "organizer_v2_1" and run["engine"]["engine"] == "engine_surge"
    assert run["input_label"] == "uploaded case, no reference ruling" and run["expected_check"] is None
    assert fake.requests and not any(name.lower() in r["user"].lower() for r in fake.requests) and any(code in r["user"] for r in fake.requests)
    assert name.lower() not in json.dumps(run, ensure_ascii=False).lower()       # the run record holds the pseudonymized view only


def _example_with(**changes) -> bytes:
    ex = U.example_upload()
    ex.update(changes)
    return json.dumps(ex).encode()


@pytest.mark.parametrize("data, says", [
    (b"this is not json", "not valid JSON"),
    (b"\xff\xfe\x00", "not UTF-8"),
    (b"[1, 2, 3]", "one JSON object"),
    (b"{}", "dispute_ticket is missing"),
    (json.dumps({"dispute_ticket": {"dispute_type": "fare_dispute", "filed_by": "rider"}}).encode(), "dispute_ticket.description is missing"),
    (_example_with(rider_profile=[]), "rider_profile is missing or is not an object"),
    (_example_with(trip_data={}), "does not fit the organizer's sample format"),
    (b" " * (U.MAX_UPLOAD_BYTES + 1), "the limit is 1 MB"),
])
def test_an_upload_that_does_not_fit_is_refused_with_a_clear_message(data, says):
    with pytest.raises(U.InvalidCase, match=says):
        U.parse_upload(data)


def test_the_stages_only_run_calls_no_model_and_holds_the_pseudonymized_view():
    name, _code = first_name_term(cases.load_case("DISP-001"))
    cid, raw, profile = U.edited_case("DISP-001", f"{name} here. The route was far too long.")
    run = pipeline.run_stages(cid, raw, profile=profile, input_label=U.EDITED_LABEL)
    assert run["mode"] == "stages" and run["messages"] == [] and run["result"] is None and run["engine"]["outcome"] == "PARTIAL_REFUND"
    assert name.lower() not in json.dumps(run, ensure_ascii=False).lower()


@pytest.mark.parametrize("choice, has_key, code_required, unlocked, used, custom, mode", [
    ("Auto", True, True, False, 0, False, "mock"),       # Auto never goes live without the access code
    ("Live", True, True, False, 0, False, "mock"),
    ("Auto", True, True, True, 0, False, "live"),
    ("Auto", True, False, False, 0, False, "live"),      # no access code configured: a private deployment
    ("Live", False, False, False, 0, False, "mock"),
    ("Auto", True, True, True, U.LIVE_RUN_CAP, False, "mock"),
    ("Auto", True, True, False, 0, True, "stages"),      # an edited or uploaded case without live mode: deterministic stages only
    ("Mock", True, True, True, 0, True, "stages"),
    ("Live", True, True, True, 3, True, "live"),
])
def test_live_mode_follows_the_key_the_access_code_and_the_run_cap(choice, has_key, code_required, unlocked, used, custom, mode):
    got, why = U.decide_mode(choice, has_key=has_key, code_required=code_required, unlocked=unlocked, live_runs_used=used, custom=custom)
    assert got == mode
    assert (why is None) == (has_key and (unlocked or not code_required) and used < U.LIVE_RUN_CAP)


def test_secrets_come_from_st_secrets_then_the_environment_and_the_code_check_is_exact():
    class NoSecretsFile:
        def get(self, name):
            raise FileNotFoundError("no secrets.toml")
    assert U.secret("LIVE_ACCESS_CODE", {"LIVE_ACCESS_CODE": "abc"}, environ={"LIVE_ACCESS_CODE": "env"}) == "abc"
    assert U.secret("LIVE_ACCESS_CODE", NoSecretsFile(), environ={"LIVE_ACCESS_CODE": "env"}) == "env"
    assert U.secret("LIVE_ACCESS_CODE", None, environ={}) == ""
    assert U.code_ok("abc", "abc") and not U.code_ok("abd", "abc") and not U.code_ok("", "") and not U.code_ok("abc", "")


def test_the_app_loads_and_an_edited_complaint_runs_the_stages_only_without_a_key():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(U.config.APP_DIR / "app.py"), default_timeout=120).run()
    assert not at.exception
    at.sidebar.checkbox[0].uncheck()
    at.sidebar.text_area[0].input("The driver took a much longer route and never told me why. I want a refund.").run()
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert any("Deterministic stages only" in i.value for i in at.info) and any("Edited case, no reference ruling" in c.value for c in at.caption)

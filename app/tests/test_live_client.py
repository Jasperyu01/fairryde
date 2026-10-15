"""Live mode against a fake Anthropic client: the request is what the API expects, replies are parsed, and a refusal or an API failure escalates."""
import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from fairryde_app import config, llm, pipeline


class FakeAPI:
    """Replays the saved answers as if the model had said them. Records every call."""

    def __init__(self, case_id, wrap="fence", fail=None):
        self.fx = json.loads((config.MOCK_DIR / f"{case_id}.json").read_text(encoding="utf-8"))["responses"]
        self.calls, self.wrap, self.fail = [], wrap, fail
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create_beta))
        self.messages = SimpleNamespace(create=self._create)

    def _agent_of(self, kw):
        user = kw["messages"][0]["content"]
        payload = json.loads(user.split("<case_file>")[1].split("</case_file>")[0])
        agent = ("judge" if "engine_result" in payload else "driver_advocate" if "rider_advocate_brief" in payload else "rider_advocate")
        return agent, payload["mode"]

    def _reply(self, kw):
        self.calls.append(kw)
        if self.fail:
            r = self.fail(len(self.calls), kw)
            if r is not None:
                return r
        agent, mode = self._agent_of(kw)
        data = self.fx.get(f"{agent}:{mode}") or self.fx[agent]
        text = json.dumps(data)
        text = f"```json\n{text}\n```" if self.wrap == "fence" else f"Here is my answer.\n{text}" if self.wrap == "prose" else text
        usage = SimpleNamespace(input_tokens=1200, output_tokens=400, cache_creation_input_tokens=0, cache_read_input_tokens=0)
        return SimpleNamespace(content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)], usage=usage, stop_reason="end_turn",
                               model="claude-sonnet-5-5", _request_id=f"req_{len(self.calls)}")

    def _create_beta(self, **kw):
        return self._reply(kw)

    def _create(self, **kw):
        return self._reply(kw)


def live_client(fake) -> llm.AnthropicClient:
    c = llm.AnthropicClient.__new__(llm.AnthropicClient)
    c._anthropic, c.client = anthropic, fake
    return c


def test_request_shape_and_pipeline_result():
    fake = FakeAPI("DISP-003")
    run = pipeline.run_case("DISP-003", client=live_client(fake), save=False)
    assert run["mode"] == "live" and run["model"] == "claude-sonnet-5-5"
    assert (run["result"]["outcome"], run["result"]["amount_sgd"], run["result"]["tier"]) == ("FULL_REFUND", 4.5, "AUTO")
    assert len(fake.calls) == 3
    kw = fake.calls[0]
    assert kw["model"] == "claude-sonnet-5-5" and kw["fallbacks"] == "default" and kw["betas"] == ["server-side-fallback-2026-07-01"]
    assert "temperature" not in kw and "top_p" not in kw and "tool_choice" not in kw and "thinking" not in kw      # Sonnet 5.5 takes none of these
    assert kw["output_config"] == {"effort": config.EFFORT} and kw["max_tokens"] == config.MAX_TOKENS
    assert kw["system"][-1]["cache_control"] == {"type": "ephemeral"} and kw["messages"][0]["role"] == "user"
    assert run["messages"][0]["usage"]["input_tokens"] == 1200 and run["messages"][0]["request_id"] == "req_1"


@pytest.mark.parametrize("wrap", ["fence", "prose", "plain"])
def test_replies_are_parsed_whatever_surrounds_the_json(wrap):
    run = pipeline.run_case("DISP-003", client=live_client(FakeAPI("DISP-003", wrap=wrap)), save=False)
    assert run["result"]["outcome"] == "FULL_REFUND" and run["result"]["gate"] is None


def test_an_unreadable_reply_gets_one_repair_attempt():
    def fail(n, kw):
        if n == 1:
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="I think the rider should get a refund.")], usage=SimpleNamespace(input_tokens=1, output_tokens=1,
                                   cache_creation_input_tokens=0, cache_read_input_tokens=0), stop_reason="end_turn", model="m", _request_id="r")
    fake = FakeAPI("DISP-003", fail=fail)
    run = pipeline.run_case("DISP-003", client=live_client(fake), save=False)
    assert len(fake.calls) == 4 and "could not be read as JSON" in fake.calls[1]["messages"][0]["content"]
    assert run["result"]["outcome"] == "FULL_REFUND"


def test_a_refusal_by_the_model_escalates_instead_of_ruling():
    def fail(n, kw):
        if "engine_result" in kw["messages"][0]["content"]:
            return SimpleNamespace(content=[], usage=SimpleNamespace(input_tokens=1, output_tokens=0, cache_creation_input_tokens=0, cache_read_input_tokens=0), stop_reason="refusal",
                                   stop_details=SimpleNamespace(category="general_harms"), model="m", _request_id="r")
    run = pipeline.run_case("DISP-003", client=live_client(FakeAPI("DISP-003", fail=fail)), save=False)
    r = run["result"]
    assert r["gate"] == "G7" and r["tier"] == "APPROVE" and r["outcome"] == "FULL_REFUND" and "declined" in r["reasoning"] and r["case_file"] is not None


def test_an_api_outage_escalates_instead_of_ruling():
    def fail(n, kw):
        raise anthropic.APIConnectionError(request=httpx2.Request("POST", "http://x"))
    run = pipeline.run_case("DISP-001", client=live_client(FakeAPI("DISP-001", fail=fail)), save=False)
    assert run["result"]["tier"] == "HUMAN" or run["result"]["gate"] == "G7"
    assert all(m["error"] for m in run["messages"])


def test_the_fallback_parameter_is_dropped_when_the_api_does_not_know_it():
    class NoFallbacks(FakeAPI):
        def _create_beta(self, **kw):
            raise anthropic.BadRequestError("fallbacks: unknown parameter", response=httpx2.Response(400, request=httpx2.Request("POST", "http://x")), body=None)
    fake = NoFallbacks("DISP-003")
    run = pipeline.run_case("DISP-003", client=live_client(fake), save=False)
    assert run["result"]["outcome"] == "FULL_REFUND" and all("fallbacks" not in c for c in fake.calls)


def test_record_keeps_the_models_answers_as_saved_responses(tmp_path, monkeypatch):
    fake = FakeAPI("DISP-003")                       # reads the real fixtures first; then the recording goes to a temporary directory
    monkeypatch.setattr(config, "MOCK_DIR", tmp_path)
    monkeypatch.setattr(pipeline.config, "MOCK_DIR", tmp_path)
    pipeline.run_case("DISP-003", client=live_client(fake), save=False, record=True)
    fx = json.loads((tmp_path / "DISP-003.json").read_text(encoding="utf-8"))
    assert fx["source"] == "recorded from a live run" and set(fx["responses"]) == {"rider_advocate", "driver_advocate", "judge"}


def test_auto_mode_is_mock_without_a_key_and_live_with_one(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm.default_mode() == "mock"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert llm.default_mode() == "live"

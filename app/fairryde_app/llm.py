"""LLM access: the Anthropic API (live) or saved responses (mock).

Live: the anthropic SDK, model claude-sonnet-5-5, key from ANTHROPIC_API_KEY (the SDK also resolves an `ant auth login` profile). Claude Sonnet 5.5
takes no sampling parameters and no forced tool use, so the agents are asked for one JSON object and the reply is parsed; thinking runs at the
model's default (adaptive) and output_config.effort sets how hard it works. The server-side refusal fallback is requested by default (it exists on
the Claude API only; if the API rejects the parameter, the call is repeated without it). A refusal or an API failure never raises into the
pipeline as a ruling: it comes back as an LLMResult with `refused` or `error` set, and the pipeline escalates.

Mock: replays app/mock_responses/<case_id>.json, so the demo works offline. MOCK_SCENARIOS change the saved Judge answer on purpose, to show
the verifier at work (a disagreement, a citation error, a low confidence, a late safety flag).
"""
from __future__ import annotations

import copy
import json
import os
import time
from dataclasses import dataclass, field

from . import config

MOCK_SCENARIOS = {
    "normal": "Replay the saved answers as they are.",
    "judge_disagrees": "The Judge rules differently from the rules engine (gate G8: a human decides, with the full case file).",
    "bad_citation_fixed": "The Judge cites an evidence ID that does not exist; the verifier sends it back once and the retry is clean.",
    "bad_citation": "The Judge keeps citing an ID that does not exist after the retry (gate G7: the engine's ruling stays provisional, tier APPROVE).",
    "low_confidence": "The Judge reports a confidence of 0.55, below the Section 6 threshold (escalation with the recommended ruling).",
    "late_safety_flag": "The Judge notices safety content by meaning that the keyword check missed (Section 5.2: the ruling is withdrawn).",
}


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResult:
    text: str = ""
    usage: dict = field(default_factory=dict)
    model: str = ""
    mock: bool = False
    latency_s: float = 0.0
    request_id: str | None = None
    stop_reason: str | None = None
    refused: bool = False
    error: str | None = None
    served_by: str | None = None


class AnthropicClient:
    name = "live"

    def __init__(self, api_key: str | None = None):
        import anthropic
        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=180.0) if api_key else anthropic.Anthropic(max_retries=2, timeout=180.0)

    def complete(self, *, agent: str, system_blocks: list[dict], user: str, case_id: str, attempt: int = 0, **_ignored) -> LLMResult:
        a = self._anthropic
        kwargs = dict(model=config.MODEL, max_tokens=config.MAX_TOKENS, system=system_blocks, messages=[{"role": "user", "content": user}],
                      output_config={"effort": config.EFFORT})
        t0 = time.time()
        try:
            try:
                if config.USE_FALLBACKS:
                    msg = self.client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
                else:
                    msg = self.client.messages.create(**kwargs)
            except a.BadRequestError as exc:
                if config.USE_FALLBACKS and "fallback" in str(exc).lower():          # not offered here: repeat without it
                    msg = self.client.messages.create(**kwargs)
                else:
                    raise
        except a.AuthenticationError as exc:
            return LLMResult(error=f"authentication failed: {exc.message}", model=config.MODEL, latency_s=time.time() - t0)
        except a.APIStatusError as exc:
            return LLMResult(error=f"API error {exc.status_code}: {exc.message}", model=config.MODEL, latency_s=time.time() - t0)
        except a.APIConnectionError as exc:
            return LLMResult(error=f"network error: {exc}", model=config.MODEL, latency_s=time.time() - t0)
        text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
        usage = {k: getattr(msg.usage, k, None) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")}
        refused = msg.stop_reason == "refusal"
        err = None
        if refused:
            sd = getattr(msg, "stop_details", None)
            err = f"the model declined this request (category: {getattr(sd, 'category', None)})"
        return LLMResult(text=text, usage=usage, model=getattr(msg, "model", config.MODEL), latency_s=round(time.time() - t0, 2), request_id=getattr(msg, "_request_id", None),
                         stop_reason=msg.stop_reason, refused=refused, error=err)


class MockMissing(LookupError):
    pass


class MockClient:
    name = "mock"

    def __init__(self, scenario: str = "normal", mock_dir=None, delay_s: float = 0.0):
        if scenario not in MOCK_SCENARIOS:
            raise ValueError(f"unknown mock scenario {scenario!r}; one of {', '.join(MOCK_SCENARIOS)}")
        self.scenario, self.dir, self.delay_s = scenario, mock_dir or config.MOCK_DIR, delay_s

    def fixture(self, case_id: str) -> dict:
        path = self.dir / f"{case_id}.json"
        if not path.exists():
            raise MockMissing(f"no saved responses for {case_id} in {self.dir}")
        return json.loads(path.read_text(encoding="utf-8"))

    def complete(self, *, agent: str, system_blocks=None, user: str = "", case_id: str, attempt: int = 0, mode: str = "ruling", **_ignored) -> LLMResult:
        fx = self.fixture(case_id)
        resp = copy.deepcopy(fx["responses"][f"{agent}:{mode}"] if f"{agent}:{mode}" in fx["responses"] else fx["responses"][agent])
        if agent == "judge" and mode == "ruling":
            resp = apply_scenario(self.scenario, resp, attempt)
        if self.delay_s:
            time.sleep(self.delay_s)
        text = resp if isinstance(resp, str) else json.dumps(resp, ensure_ascii=False)
        return LLMResult(text=text, usage={"input_tokens": 0, "output_tokens": 0}, model="mock (saved response)", mock=True, stop_reason="end_turn")


def apply_scenario(scenario: str, j: dict, attempt: int) -> dict:
    """Change a saved Judge answer on purpose, to show what the verifier does with it."""
    if scenario == "normal" or not isinstance(j, dict):
        return j
    if scenario == "judge_disagrees":
        if j.get("outcome") in ("PARTIAL_REFUND", "FULL_REFUND", "WAIVE_FEE", "TOLL_REFUND", "GOODWILL_CREDIT"):
            j.update(outcome="UPHOLD", amount_sgd=None, payer=None, payee=None, agreement_with_engine=False,
                     disagreement_note="Demo scenario: the Judge reads the records differently and would uphold the charge without a refund.")
        else:
            j.update(outcome="WAIVE_FEE", amount_sgd=5.0, payer="PLATFORM", payee="RIDER", agreement_with_engine=False,
                     disagreement_note="Demo scenario: the Judge reads the records differently and would waive the fee.")
    elif scenario == "bad_citation_fixed" and attempt == 0:
        j["evidence"] = list(j.get("evidence", [])) + ["E-XYZ-99"]
        j["reasoning"] = str(j.get("reasoning", "")) + " The tow record [E-XYZ-99] also supports this."
    elif scenario == "bad_citation":
        j["evidence"] = list(j.get("evidence", [])) + ["E-XYZ-99"]
        j["rules"] = list(j.get("rules", [])) + ["FC-R99"]
    elif scenario == "low_confidence":
        j["confidence"] = 0.55
    elif scenario == "late_safety_flag":
        j["safety_concern"] = True
    return j


def make_client(mode: str, scenario: str = "normal", delay_s: float = 0.0):
    if mode == "mock":
        return MockClient(scenario=scenario, delay_s=delay_s)
    if mode == "live":
        return AnthropicClient()
    raise ValueError(f"mode must be 'mock' or 'live', not {mode!r}")


def default_mode() -> str:
    """live when an API key is set, else mock (CLAUDE.md: the demo must always work offline)."""
    return "live" if os.environ.get("ANTHROPIC_API_KEY") else "mock"

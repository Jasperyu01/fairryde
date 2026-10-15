"""Test setup: the app package on sys.path, no API key (so mock mode is the default), and run logs in a temporary directory."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.setdefault("FAIRRYDE_RUNS_DIR", tempfile.mkdtemp(prefix="fairryde_runs_"))

import pytest                                     # noqa: E402

from fairryde_app import llm, pipeline            # noqa: E402

REQUIRED_CASES = ["DISP-001", "DISP-002", "DISP-003", "E01", "E02", "E03", "E04", "E10", "E11"]
_CACHE: dict = {}


def run_mock(case_id: str, scenario: str = "normal", **kw) -> dict:
    """One mock-mode run, cached for the 'normal' scenario (the pipeline is deterministic in mock mode)."""
    if scenario == "normal" and not kw:
        if case_id not in _CACHE:
            _CACHE[case_id] = pipeline.run_case(case_id, mode="mock", scenario=scenario, save=False)
        return _CACHE[case_id]
    return pipeline.run_case(case_id, mode="mock", scenario=scenario, save=False, **kw)


class SpyClient(llm.MockClient):
    """A mock client that keeps every request it receives, and can change a saved answer before replaying it."""

    def __init__(self, scenario: str = "normal", tamper=None):
        super().__init__(scenario=scenario)
        self.requests: list[dict] = []
        self.tamper = tamper

    def complete(self, *, agent, system_blocks=None, user="", case_id, attempt=0, mode="ruling", **kw):
        self.requests.append({"agent": agent, "system": [b["text"] for b in (system_blocks or [])], "user": user, "mode": mode, "attempt": attempt})
        res = super().complete(agent=agent, system_blocks=system_blocks, user=user, case_id=case_id, attempt=attempt, mode=mode, **kw)
        if self.tamper:
            import json
            data = json.loads(res.text)
            data = self.tamper(agent, mode, attempt, data) or data
            res.text = json.dumps(data)
        return res


@pytest.fixture
def spy():
    return SpyClient

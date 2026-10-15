"""Paths and settings. Nothing here reads a secret except through the environment (ANTHROPIC_API_KEY)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "app"
KB_DIR = ROOT / "kb"
KB_TOOLS = KB_DIR / "tools"
PROMPTS_DIR = APP_DIR / "prompts"
MOCK_DIR = APP_DIR / "mock_responses"
RUNS_DIR = Path(os.environ.get("FAIRRYDE_RUNS_DIR", APP_DIR / "runs"))
SAMPLE_CASES_DIR = APP_DIR / "sample_cases"
VALIDATION_DIR = ROOT / "validation"
VALIDATION_CASES_DIR = VALIDATION_DIR / "V4_e2e" / "cases"
POLICY_V21_PATH = KB_DIR / "sources" / "organizer" / "policy_v2.1.md"

# The user asked for claude-sonnet-5-5. FAIRRYDE_MODEL overrides it for experiments.
MODEL = os.environ.get("FAIRRYDE_MODEL", "claude-sonnet-5-5")
MAX_TOKENS = int(os.environ.get("FAIRRYDE_MAX_TOKENS", "8000"))
EFFORT = os.environ.get("FAIRRYDE_EFFORT", "medium")          # output_config.effort; Sonnet 5.5 defaults to high
USE_FALLBACKS = os.environ.get("FAIRRYDE_FALLBACKS", "1") != "0"  # server-side refusal fallback (Claude API only)

JUDGE_MAX_RETRIES = 1        # AUTH-04 gate G7: one retry after a citation or number failure, then approval
SAFETY_MODE_AGENTS = ("rider_advocate", "driver_advocate", "judge")

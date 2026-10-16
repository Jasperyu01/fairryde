"""New input for the public app: an edited complaint, an uploaded case, and who may use live mode.

An edited case is a copy of a listed case with a new complaint text; it keeps its policy profile. An uploaded case is a JSON file in the
organizer's sample format; it runs under organizer_v2_1. Neither has a reference ruling, and neither has saved answers, so the agents need
live mode. Both go through the same pipeline (case adapter, intake, pseudonymization, leak check) as a listed case.
"""
from __future__ import annotations

import copy
import hmac
import json
import re

from . import cases, config, intake, pipeline
from .kbaccess import ORGANIZER_PROFILE, case_adapter, kbload

MAX_UPLOAD_BYTES = 1_000_000
LIVE_RUN_CAP = 10
EDITED_LABEL = "edited case, no reference ruling"
UPLOADED_LABEL = "uploaded case, no reference ruling"
EXAMPLE_ID = "UPLOAD-EXAMPLE-01"           # the run id of an upload is UPLOAD-<dispute_id>, so this one keeps its name


class InvalidCase(ValueError):
    """The uploaded file does not fit the organizer's sample format; the message says why, in words a visitor can act on."""


# ------------------------------------------------------------------ edited complaint
def complaint_of(raw: dict) -> str:
    return str((raw.get("dispute_ticket") or {}).get("description") or "")


def with_complaint(raw: dict, text: str) -> dict:
    """A copy of the case with a new complaint text (dispute_ticket.description); the original is not changed."""
    c = copy.deepcopy(raw)
    c["dispute_ticket"]["description"] = text
    return c


def profile_of(case_id: str) -> str:
    """The policy profile a listed case runs under (an edited copy keeps it)."""
    info = cases.get_info(case_id)
    if info.profile_override:
        return info.profile_override
    canon, _ = case_adapter.prepare(cases.load_case(case_id))
    return kbload.default_profile(canon)


def edited_case(case_id: str, text: str) -> tuple[str, dict, str]:
    """(run id, case, profile) for a listed case with an edited complaint."""
    return f"{case_id}-EDITED", with_complaint(cases.load_case(case_id), text), profile_of(case_id)


# ------------------------------------------------------------------ upload
def example_upload() -> dict:
    """An example upload built from our own synthetic sample (app/sample_cases/DEMO-SAFETY-01), not from the organizer's files:
    the same trip and surge log as a plain fare dispute, with the safety content taken out."""
    c = copy.deepcopy(next(json.loads(p.read_text(encoding="utf-8")) for p in sorted(config.SAMPLE_CASES_DIR.glob("*.json"))
                           if json.loads(p.read_text(encoding="utf-8"))["dispute_ticket"]["dispute_id"] == "DEMO-SAFETY-01"))
    for k in [k for k in c if k.startswith("_")]:
        c.pop(k)
    tk = c["dispute_ticket"]
    tk["dispute_id"] = EXAMPLE_ID
    tk["description"] = "The final fare was $16.50 but the upfront quote was $12.00 and nobody told me about surge. I want the $4.50 difference back."
    c["chat_logs"] = [m for m in c["chat_logs"] if m["message_id"] in ("MSG-001", "MSG-002", "MSG-003")]
    c["chat_logs"][-1]["message"] = "The fare is $16.50, why? The quote was $12."
    return c


def _need(obj, key: str, kind, where: str):
    if not isinstance(obj.get(key), kind):
        what = "an object" if kind is dict else "a list" if kind is list else "text"
        raise InvalidCase(f"{where}{key} is missing or is not {what}.")
    return obj[key]


def parse_upload(data: bytes) -> tuple[str, dict]:
    """(run id, case) for an uploaded file, or InvalidCase with a clear message. Checks the size and the format, then runs the case adapter,
    the intake and the reference engine on it, so a file that would break a stage is refused here and not halfway through a run."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise InvalidCase(f"The file is {len(data):,} bytes; the limit is 1 MB ({MAX_UPLOAD_BYTES:,} bytes).")
    try:
        raw = json.loads(data.decode("utf-8"))
    except UnicodeDecodeError:
        raise InvalidCase("The file is not UTF-8 text. Upload a .json file.") from None
    except json.JSONDecodeError as exc:
        raise InvalidCase(f"The file is not valid JSON (line {exc.lineno}, column {exc.colno}: {exc.msg}).") from None
    except RecursionError:
        raise InvalidCase("The JSON is nested too deeply.") from None
    if not isinstance(raw, dict):
        raise InvalidCase("The file must hold one JSON object (one case), in the format of the example file.")
    tk = _need(raw, "dispute_ticket", dict, "")
    for key in ("dispute_type", "description", "filed_by"):
        _need(tk, key, str, "dispute_ticket.")
    for key in ("trip_data", "rider_profile", "driver_profile"):
        _need(raw, key, dict, "")
    if "chat_logs" in raw:
        _need(raw, "chat_logs", list, "")
    given = re.sub(r"[^A-Za-z0-9-]", "", str(tk.get("dispute_id") or ""))[:40] or "CASE"
    case_id = given if given.startswith("UPLOAD-") else "UPLOAD-" + given
    validate(case_id, raw, ORGANIZER_PROFILE)
    return case_id, raw


def validate(case_id: str, raw: dict, profile: str) -> dict:
    """Run the deterministic stages (case adapter, intake, evidence, engine); any failure becomes InvalidCase."""
    try:
        return pipeline.run_stages(case_id, raw, profile=profile)
    except InvalidCase:
        raise
    except Exception as exc:                       # noqa: BLE001  a stage that cannot read the file: say which part, never a traceback
        raise InvalidCase(f"The file does not fit the organizer's sample format: {type(exc).__name__}: {str(exc)[:200]}. Compare it with the example file.") from None


# ------------------------------------------------------------------ live mode on a public app
def secret(name: str, secrets=None, environ=None) -> str:
    """A setting from st.secrets, falling back to the environment. Never printed or logged by the app."""
    if secrets is not None:
        try:
            v = secrets.get(name)
            if v:
                return str(v)
        except Exception:                          # noqa: BLE001  no secrets.toml: Streamlit raises; fall back to the environment
            pass
    import os
    return (environ if environ is not None else os.environ).get(name, "") or ""


def code_ok(entered: str, expected: str) -> bool:
    return bool(expected) and hmac.compare_digest(str(entered or "").encode(), str(expected).encode())


def decide_mode(choice: str, *, has_key: bool, code_required: bool, unlocked: bool, live_runs_used: int, custom: bool) -> tuple[str, str | None]:
    """(mode, why live is off). mode is live, mock (replay the saved answers of a listed case) or stages (an edited or uploaded case
    without live mode: the deterministic stages only). Auto and Live never go live without the access code when one is set."""
    why = (None if has_key and (unlocked or not code_required) and live_runs_used < LIVE_RUN_CAP else
           "no API key is configured on this server" if not has_key else
           "live mode needs the access code" if code_required and not unlocked else
           f"the limit of {LIVE_RUN_CAP} live runs for this browser session is reached")
    wants_live = choice in ("Auto", "Live") and why is None
    if custom:
        return ("live" if wants_live else "stages"), why
    return ("live" if wants_live else "mock"), why

"""Import the knowledge base and its reference engines (kb/tools) without changing them.

The engines use bare imports (import case_adapter), so kb/tools goes on sys.path. The KB is read-only for the app.
"""
from __future__ import annotations

import sys
from functools import lru_cache

from .config import KB_TOOLS

if str(KB_TOOLS) not in sys.path:
    sys.path.insert(0, str(KB_TOOLS))

import case_adapter           # noqa: E402,F401
import engine_noshow          # noqa: E402,F401
import engine_route           # noqa: E402,F401
import engine_surge           # noqa: E402,F401
import engine_toll            # noqa: E402,F401
import engines                # noqa: E402,F401
import explain                # noqa: E402,F401
import kbload                 # noqa: E402,F401
import policy_v21 as P21      # noqa: E402,F401
import privacy_scan           # noqa: E402,F401

ORGANIZER_PROFILE = kbload.ORGANIZER_PROFILE


@lru_cache(maxsize=1)
def get_kb() -> "kbload.KB":
    return kbload.KB()

#!/usr/bin/env python3
"""Gatekeeper: pure rule-based gate for the autonomous quant research loop.

No LLM calls, no network calls, no stdin/argv required. This script is meant
to be executed by a Hermes cronjob (hourly) BEFORE the Research Agent's LLM
turn starts. It decides whether the research loop may run right now, based
on:

  1. Day-of-week / time-of-day (KST)
  2. Claude 5-hour rolling usage window, read from ``usage_state.json``
     (see that file / README.md for the exact JSON schema and how it is
     expected to be produced — there is no real usage API wired up yet,
     this script only *consumes* the file).

Policy
------
Weekdays (Mon-Fri) 10:00-18:00 KST — "business hours":
    Treat this window as contended / cost-sensitive. Only approve running
    the loop while the 5h rolling usage is at or below ``BUSINESS_HOURS_MAX_PCT``
    (75%, i.e. always keep >=25% headroom). If usage is unknown (missing/stale
    state file) we fail closed (not approved) during business hours.

Outside business hours (weekday evenings/nights + all of Sat/Sun):
    Approve running the loop as long as usage has not hit the hard limit
    (100%). Once the limit is reached, stay blocked until the usage state
    file reports the rolling window has reset (usage below 100% again).

Output
------
Prints a single JSON object to stdout:
    {"approved": bool, "reason": str, "suggested_workload": "light|normal|max"}

Exit code is 0 if approved, 1 if not approved (so cron logs / `set -e`
callers can branch on exit code alone, without parsing JSON, if they want).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

KST = timezone(timedelta(hours=9))

# Keep at least this much headroom in the 5h rolling usage window during
# weekday business hours (10:00-18:00 KST).
BUSINESS_HOURS_MAX_PCT = 75.0

# Hard ceiling — usage state at/above this is always a hard stop, regardless
# of day/time, because Claude itself will refuse further calls anyway.
HARD_LIMIT_PCT = 100.0

BUSINESS_HOURS_START = 10  # inclusive, KST
BUSINESS_HOURS_END = 18  # exclusive, KST

DEFAULT_USAGE_STATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "usage_state.json"
)


@dataclass
class UsageState:
    usage_pct: float
    limit_reached: bool
    updated_at: Optional[str] = None
    window_reset_at: Optional[str] = None
    raw: Optional[dict] = None


class UsageStateError(RuntimeError):
    """Raised when usage_state.json is missing, unreadable, or malformed."""


def load_usage_state(path: str = DEFAULT_USAGE_STATE_PATH) -> UsageState:
    if not os.path.exists(path):
        raise UsageStateError(f"usage state file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise UsageStateError(f"failed to read/parse {path}: {exc}") from exc

    if "usage_pct" not in data:
        raise UsageStateError(f"{path} missing required field 'usage_pct'")

    usage_pct = float(data["usage_pct"])
    limit_reached = bool(data.get("limit_reached", usage_pct >= HARD_LIMIT_PCT))
    return UsageState(
        usage_pct=usage_pct,
        limit_reached=limit_reached,
        updated_at=data.get("updated_at"),
        window_reset_at=data.get("window_reset_at"),
        raw=data,
    )


def is_business_hours(now_kst: datetime) -> bool:
    """Mon-Fri 10:00-18:00 KST. Monday=0 ... Sunday=6."""
    if now_kst.weekday() >= 5:  # Sat=5, Sun=6
        return False
    return BUSINESS_HOURS_START <= now_kst.hour < BUSINESS_HOURS_END


def suggest_workload(usage_pct: float, business_hours: bool) -> str:
    """Map current usage to a suggested workload intensity.

    This is advisory only — the Research Agent should use it to decide how
    ambitious to be in a single loop iteration (e.g. skip long walk-forward
    sweeps under "light").
    """
    if business_hours:
        if usage_pct < 40:
            return "normal"
        return "light"  # 40-75%, business hours: stay conservative
    # off hours / weekend: more headroom available
    if usage_pct < 40:
        return "max"
    if usage_pct < 75:
        return "normal"
    return "light"


def evaluate(now_kst: Optional[datetime] = None, usage_state_path: str = DEFAULT_USAGE_STATE_PATH) -> dict:
    now_kst = now_kst or datetime.now(KST)
    business_hours = is_business_hours(now_kst)

    try:
        state = load_usage_state(usage_state_path)
    except UsageStateError as exc:
        if business_hours:
            # Fail closed during cost-sensitive hours: we cannot verify
            # headroom, so don't run.
            return {
                "approved": False,
                "reason": f"usage state unavailable during business hours, failing closed: {exc}",
                "suggested_workload": "light",
            }
        # Off hours: fail open at "light" workload — low risk, and blocking
        # entirely on a missing mock file would stall the whole loop.
        return {
            "approved": True,
            "reason": f"usage state unavailable outside business hours, failing open cautiously: {exc}",
            "suggested_workload": "light",
        }

    if state.limit_reached or state.usage_pct >= HARD_LIMIT_PCT:
        return {
            "approved": False,
            "reason": (
                f"5h rolling usage at {state.usage_pct:.1f}% (>= {HARD_LIMIT_PCT:.0f}%): "
                "hard limit reached, waiting for window reset "
                f"(window_reset_at={state.window_reset_at!r})"
            ),
            "suggested_workload": "light",
        }

    if business_hours:
        if state.usage_pct > BUSINESS_HOURS_MAX_PCT:
            return {
                "approved": False,
                "reason": (
                    f"weekday business hours (KST {now_kst.strftime('%H:%M')}); "
                    f"5h rolling usage {state.usage_pct:.1f}% exceeds "
                    f"{BUSINESS_HOURS_MAX_PCT:.0f}% headroom threshold"
                ),
                "suggested_workload": "light",
            }
        return {
            "approved": True,
            "reason": (
                f"weekday business hours (KST {now_kst.strftime('%H:%M')}); "
                f"usage {state.usage_pct:.1f}% within {BUSINESS_HOURS_MAX_PCT:.0f}% headroom budget"
            ),
            "suggested_workload": suggest_workload(state.usage_pct, business_hours),
        }

    # Off business hours (weekday evenings/nights) or weekend
    return {
        "approved": True,
        "reason": (
            f"outside weekday business hours / weekend (KST {now_kst.strftime('%a %H:%M')}); "
            f"usage {state.usage_pct:.1f}%, below hard limit"
        ),
        "suggested_workload": suggest_workload(state.usage_pct, business_hours),
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result))
    return 0 if result["approved"] else 1


if __name__ == "__main__":
    sys.exit(main())

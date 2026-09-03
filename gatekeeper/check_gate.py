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


# Path to the Hermes agent package that ships agent.account_usage. Overridable
# via env var for portability (e.g. different machine layout).
HERMES_AGENT_PATH = os.environ.get(
    "HERMES_AGENT_PATH", os.path.expanduser("~/.hermes/hermes-agent")
)


def load_usage_state_live() -> UsageState:
    """Fetch REAL Claude 5h rolling usage via Hermes' built-in Anthropic OAuth
    usage-API client (agent.account_usage.fetch_account_usage), which calls
    the official (undocumented) endpoint api.anthropic.com/api/oauth/usage.

    This is the ground truth: it reads the same 5-hour rolling window used by
    Claude Code / Claude Pro-Max itself (the ``five_hour`` window,
    ``utilization`` field), not an estimate derived from local logs.

    Raises UsageStateError if the Hermes module can't be imported or the API
    call fails/returns no usable window (e.g. not logged in via OAuth).
    """
    if HERMES_AGENT_PATH not in sys.path:
        sys.path.insert(0, HERMES_AGENT_PATH)
    try:
        from agent.account_usage import fetch_account_usage  # type: ignore
    except ImportError as exc:
        raise UsageStateError(
            f"could not import agent.account_usage from {HERMES_AGENT_PATH}: {exc}"
        ) from exc

    try:
        snapshot = fetch_account_usage("anthropic")
    except Exception as exc:  # network/API errors, auth errors, etc.
        raise UsageStateError(f"fetch_account_usage('anthropic') failed: {exc}") from exc

    if snapshot is None or not snapshot.available:
        reason = getattr(snapshot, "unavailable_reason", None) if snapshot else None
        raise UsageStateError(f"account usage snapshot unavailable: {reason or 'no data'}")

    five_hour = next((w for w in snapshot.windows if w.label == "Current session"), None)
    if five_hour is None or five_hour.used_percent is None:
        raise UsageStateError("account usage snapshot has no 'Current session' (5h) window")

    reset_iso = five_hour.reset_at.isoformat() if five_hour.reset_at else None
    return UsageState(
        usage_pct=float(five_hour.used_percent),
        limit_reached=float(five_hour.used_percent) >= HARD_LIMIT_PCT,
        updated_at=datetime.now(timezone.utc).isoformat(),
        window_reset_at=reset_iso,
        raw={"source": "anthropic_oauth_usage_api", "label": five_hour.label},
    )


def load_usage_state(path: str = DEFAULT_USAGE_STATE_PATH) -> UsageState:
    """Load current 5h rolling usage state.

    Primary source: the live Anthropic OAuth usage API via Hermes
    (load_usage_state_live). Falls back to the local usage_state.json mock
    file (see README.md for its schema) only if the live fetch fails, e.g.
    running this script on a machine without the Hermes agent package
    available, or a transient API/network error.
    """
    try:
        return load_usage_state_live()
    except UsageStateError as live_exc:
        if not os.path.exists(path):
            raise UsageStateError(
                f"live usage fetch failed ({live_exc}) and no fallback usage "
                f"state file found: {path}"
            ) from live_exc

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

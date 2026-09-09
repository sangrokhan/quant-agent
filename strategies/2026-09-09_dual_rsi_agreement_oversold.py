"""Strategy: Dual RSI (fast+slow period) agreement oversold-bounce,
trend-following exit (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-074):
Per The Forex Geek's "Double RSI Strategy"
(https://theforexgeek.com/double-rsi-strategy/, browser_exec fallback --
web_search DDGS returned no results for the direct query), the source's
own disclosed buy rule: load two RSI indicators of DIFFERENT periods (a
default-period RSI and a longer-period RSI), wait for BOTH to be below 30
(oversold) simultaneously, AND both showing upward momentum (turning up).
This is structurally analogous to the Double Stochastic agreement idea
tested and ACCEPTED (SPY only) earlier this same cron trigger
(2026-09-09-070), but applied to RSI instead of the stochastic oscillator.
First dual-RSI-of-different-periods agreement strategy in this repo (all
45 prior RSI strategies use a single RSI threshold, divergence, or
RSI+other-indicator combos, never two RSI periods required to agree).

Signal logic
------------
- RSI(fast_window) and RSI(slow_window), standard Wilder RSI.
- Oversold agreement: both RSI_fast and RSI_slow <= oversold_threshold.
- Upward-turn confirmation: both RSI_fast and RSI_slow are higher than
  they were 1 bar ago (both turning up, not just sitting in the oversold
  zone).
- Entry (long): oversold agreement AND upward-turn confirmation, both on
  the same bar.
- Exit: EITHER RSI (fast or slow) crosses back above `exit_threshold`
  (momentum exhausted, source doesn't specify an exact exit level; this
  repo uses a symmetric-ish exit near the midline), OR a `max_hold_days`
  time-stop (source relies on price-action stops which aren't
  reproducible here; time-stop substituted per repo convention).
- Flat otherwise; long-only, no shorting (per SAFETY.md).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 14,
    slow_window: int = 21,
    oversold_threshold: float = 30.0,
    exit_threshold: float = 55.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi_fast = _rsi(close, fast_window)
    rsi_slow = _rsi(close, slow_window)

    oversold_agreement = (rsi_fast <= oversold_threshold) & (rsi_slow <= oversold_threshold)
    turning_up = (rsi_fast > rsi_fast.shift(1)) & (rsi_slow > rsi_slow.shift(1))

    entry = oversold_agreement.fillna(False) & turning_up.fillna(False)
    exit_signal = (rsi_fast > exit_threshold) | (rsi_slow > exit_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

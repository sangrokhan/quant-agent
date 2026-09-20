"""Strategy: Rate of Change (ROC) sharp-decline entry / sharp-recovery exit,
long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl, this entry's id):
Per QuantifiedStrategies' Facebook video ("A 71.2% win rate came from one
indicator and two simple thresholds", read via browser_exec after
web_search's DDGS backend TLS-erroring on the ROC-strategy follow-up
query): a backtested Rate-of-Change strategy on SPY (1993-2026) claims 146
trades, 71.2% win rate, 2.40 profit factor, $1->$9.15, 29% max drawdown,
using these rules:
  1. ROC(7) closes below -3% -> buy SPY at the next open
  2. ROC(7) closes above +3% -> sell SPY at the next open
This is a sharp-short-term-decline entry / sharp-short-term-recovery exit
scheme -- distinct from the 33 prior ROC-based entries in this repo (none
combine a symmetric +/-3% ROC(7) threshold cross with a next-day-open
execution timing exactly this way; existing entries use ROC(2), ROC(12),
PercentRank(ROC), or ROC as a sizing/gating input rather than this specific
symmetric-threshold entry/exit design). Adapted to this repo's daily-bar,
no-open-vs-close-distinction convention: since our other strategies trade
on the signal bar's own close->next-close (position.shift(1) applied to
daily returns), the "buy/sell at next open" timing in the source is
approximated by entering/exiting on the bar AFTER the ROC(7) threshold
cross is confirmed (position becomes active starting the following bar's
return), matching this repo's existing shift(1) convention rather than
literally modeling open-vs-close execution.

Signal logic
------------
- ROC(roc_window) = 100 * (close / close.shift(roc_window) - 1), a percent
  rate-of-change oscillator.
- Entry (long): ROC(roc_window) closes below entry_threshold (default -3.0,
  i.e. -3%), signaling a sharp recent decline.
- Exit: ROC(roc_window) closes above exit_threshold (default +3.0, i.e.
  +3%), signaling the recovery/rally has run its course, OR max_hold_days
  elapses (safety backstop not in the source, added per this repo's
  standard practice to bound worst-case single-trade duration).

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    roc_window: int = 7,
    entry_threshold: float = -3.0,
    exit_threshold: float = 3.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    roc = 100.0 * (close / close.shift(roc_window) - 1.0)

    entry = roc < entry_threshold
    exit_signal = roc > exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_arr = entry.fillna(False).values
    exit_arr = exit_signal.fillna(False).values
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_arr[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_arr[i]):
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

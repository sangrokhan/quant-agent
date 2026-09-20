"""Strategy: 21-Day High Breakout + 200d Trend + 126d Momentum Triple Gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-126):
Source: https://finlab.finance/en/blog/us-breakout-trend-strategy (visited
via browser_exec this iteration).

A fresh N-day (21-trading-day) high in an index ETF carries directional
information only when the broader trend agrees: source finds breakouts
filtered by trend context were positive 82% of the time 3 months later,
vs 61% for unfiltered breakouts. The full risk-on gate requires THREE
conditions simultaneously:
  1. Breakout trigger: close > prior 21-day high, with the trigger
     staying "active" (still counted as a live signal) for entry_persist
     sessions after it first fires (not just the single trigger day).
  2. Trend filter: close > SMA(200).
  3. Momentum confirmation: trailing 126-day return > 0.

Source executes this via a leveraged-ETF rotation (2x leveraged growth
ETFs in risk-on, bonds/gold/cash in risk-off); this repo adapts it to a
plain long/flat position on the base asset itself (no leverage, no hedge
substitution), consistent with the interface contract's single-asset
long/flat convention.

Distinct from every other Donchian/breakout-family strategy already in
this repo:
- 2026-09-03-008 (Donchian + 200d SMA trend filter): uses a continuous
  N-day-high entry with an N/2-day-low TRAILING STOP exit, no persistence
  window, no momentum leg. This strategy adds the 126-day absolute
  momentum condition and a discrete "trigger stays live for 5 sessions"
  entry-persistence mechanic, and exits purely on regime-condition flip
  (not a Donchian trailing stop).
- 0 prior "21-day high" entries in this repo's index (all prior breakout
  entries use 5/10/20/50/52-week windows, not exactly 21 trading days).

Signal logic
------------
- breakout_trigger = close > rolling(21)-day high (excluding today)
- breakout_active = breakout_trigger was True at any point in the last
  entry_persist (default 5) sessions (persistence window)
- trend_ok = close > SMA(trend_window)
- momentum_ok = close / close.shift(mom_window) - 1 > 0
- risk_on = breakout_active AND trend_ok AND momentum_ok
- position = 1 while risk_on, 0 otherwise (long/flat, no leverage)

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} long/flat)
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
    breakout_window: int = 21,
    entry_persist: int = 5,
    trend_window: int = 200,
    mom_window: int = 126,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rolling_high = close.rolling(breakout_window).max().shift(1)
    breakout_trigger = (close > rolling_high).fillna(False)
    breakout_active = breakout_trigger.rolling(entry_persist, min_periods=1).max().astype(bool)

    sma = close.rolling(trend_window).mean()
    trend_ok = (close > sma).fillna(False)

    mom = close / close.shift(mom_window) - 1.0
    momentum_ok = (mom > 0.0).fillna(False)

    risk_on = breakout_active & trend_ok & momentum_ok
    position = risk_on.astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's regime determines today's
    # exposure (avoid look-ahead bias -- can't act on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

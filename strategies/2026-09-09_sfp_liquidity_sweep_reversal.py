"""Strategy: Swing Failure Pattern (SFP) bullish liquidity-sweep reversal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-087):
Per https://www.quantvps.com/blog/swing-failure-pattern-strategy (accessed via
browser_exec fallback; web_search's DDGS backend errored with a TLS
connection error), a "bullish SFP" is a price-action liquidity-sweep pattern:
price briefly dips below a prior rolling N-bar swing low (sweeping resting
stop-loss orders / triggering a false breakdown) but the SAME bar closes back
ABOVE that swing-low level, with a long lower wick showing the breakdown was
rejected. The source's own stated rule: enter at the open of the candle
immediately after the SFP confirmation bar closes; place a protective stop
below the sweep candle's low (the wick extreme); exit at a fixed
risk-reward target (source suggests 1:2/1:3) or when price reverts back
above the confirmation level (the swing low being defended). This is the
first liquidity-sweep / stop-hunt / SFP-family strategy tested in this repo
(distinct from Turtle Soup 2026-09-04-076, which fades an N-day LOW BREAK on
the *next day's* close crossing back above rather than requiring the
sweep-and-reject to occur within the SAME bar via the low wick, and distinct
from Adjusted Failed Bounce 2026-09-05-019, which is IBS-based rather than
swing-low-based).

Signal logic
------------
- swing_low = rolling min(low) over `swing_lookback` bars, computed on data
  PRIOR to the current bar (shifted by 1) so the swing low is a genuine
  historical reference level, not lookahead.
- SFP confirmation bar: low[t] < swing_low[t] (the wick sweeps below the
  prior swing low) AND close[t] > swing_low[t] (closes back above it,
  rejecting the breakdown) -- both required same-bar, per source.
- Entry: long at the bar AFTER the SFP confirmation bar (i.e. position is
  set to 1 starting the next bar, consistent with the shift-by-1 convention
  used throughout this repo's generate_returns to avoid lookahead).
- Exit: close crosses back below the SFP bar's own low (stop-loss beyond the
  sweep wick extreme, source's own stated risk rule) OR a
  risk_reward-multiple target measured off the entry price and the initial
  stop distance is hit OR a max_hold_days time-stop backstop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    swing_lookback: int = 10,
    risk_reward: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    # Historical swing low reference (excludes current bar to avoid lookahead)
    swing_low = low.rolling(swing_lookback).min().shift(1)

    sfp_confirmed = (low < swing_low) & (close > swing_low)
    sfp_confirmed = sfp_confirmed.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0

    n = len(close)
    for i in range(n):
        if in_position:
            held = i - entry_idx
            c = close.iloc[i]
            if (
                c <= stop_price
                or c >= target_price
                or held >= max_hold_days
            ):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            # Enter the bar AFTER an SFP confirmation bar
            if i > 0 and bool(sfp_confirmed.iloc[i - 1]):
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
                sweep_low = low.iloc[i - 1]
                stop_price = sweep_low
                risk = max(entry_price - stop_price, 1e-9)
                target_price = entry_price + risk_reward * risk
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

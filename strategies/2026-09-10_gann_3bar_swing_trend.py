"""Strategy: Gann 3-bar swing structure trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-046):
Per justmarkets.com's Gann Swing Lines guide (visited this iteration,
https://justmarkets.com/trading-articles/forex/what-are-the-gann-swing-lines):
a 3-bar swing is an UPSWING when the 3rd bar has a higher high AND a higher
low than BOTH the 1st and 2nd bars (mirror rule for a DOWNSWING: lower high
AND lower low vs both prior bars). A confirmed series of consecutive
upswings (a "zig-zag" of higher highs/higher lows) marks an established
short-term uptrend; when that pattern breaks (a downswing forms), it
signals a potential reversal.

This is a raw bar-pattern swing-STRUCTURE construction, distinct from this
repo's existing Gann HiLo Activator strategies (2026-09-04-128,
2026-09-05-017), which build a stepped SMA-of-high/SMA-of-low trailing
support/resistance line rather than examining raw 3-bar high/low patterns
directly.

Signal logic
------------
- swing_state[t] = "up" if high[t] > max(high[t-1], high[t-2]) AND
  low[t] > max(low[t-1], low[t-2]) (higher high AND higher low vs both
  prior bars); "down" if high[t] < min(high[t-1], high[t-2]) AND
  low[t] < min(low[t-1], low[t-2]); otherwise unchanged (carry forward
  the last confirmed state, i.e. an "inside"/ambiguous bar doesn't flip
  the trend read).
- Gated by a broader SMA(trend_window) filter to avoid trading every minor
  Gann swing flip in a larger downtrend.
- Entry (long): swing_state flips to "up" AND close > SMA(trend_window).
- Exit: swing_state flips to "down", OR trend filter breaks, OR a
  max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _gann_swing_state(high: pd.Series, low: pd.Series) -> pd.Series:
    """Returns a Series of {'up','down','none'} carried-forward swing state."""
    n = len(high)
    state = pd.Series("none", index=high.index, dtype=object)
    last_state = "none"
    for i in range(2, n):
        h0, h1, h2 = high.iloc[i - 2], high.iloc[i - 1], high.iloc[i]
        l0, l1, l2 = low.iloc[i - 2], low.iloc[i - 1], low.iloc[i]
        if h2 > max(h0, h1) and l2 > max(l0, l1):
            last_state = "up"
        elif h2 < min(h0, h1) and l2 < min(l0, l1):
            last_state = "down"
        state.iloc[i] = last_state
    return state


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    swing_state = _gann_swing_state(high, low)
    swing_up = swing_state == "up"
    swing_down = swing_state == "down"
    swing_flip_up = swing_up & ~swing_up.shift(1).fillna(False)

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    entry = swing_flip_up & trend_up.fillna(False)
    exit_condition = swing_down | (~trend_up.fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_condition.iloc[i]) or held >= max_hold_days:
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

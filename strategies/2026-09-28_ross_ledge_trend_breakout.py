"""Strategy: Joe Ross "Ledge" breakout, traded in the direction of the
prevailing trend.

Hypothesis (source: https://tradingeducators.com/edition-716,
"Chart Scan with Commentary - Ledge Trade" by Joe Ross, read 2026-09-28
via browser_exec):

A Ledge (Joe Ross's "Law of Charts") is a short consolidation: "must
occur in a trend... must consist of not more than 10 bars from beginning
to end... must have two matching highs or very close to matching highs,
and two matching or very close to matching lows." The source's own
worked example trades the breakout of the ledge ONLY in the direction of
the major trend/swing (confirmed via a higher-timeframe/longer trend
check) -- i.e. this is a continuation pattern, not traded counter-trend.
0 prior "Ledge" hits in strategies_index.jsonl -- distinct from this
repo's already-tested Ross Hook (2026-09-28-066/067, a secondary-1-2-3
retracement pattern) and plain 1-2-3 reversal (2026-09-11-022/025,
2026-09-18-090/091): the Ledge is a tight two-touch consolidation
range breakout, not a swing-pivot sequence.

Mechanical proxy (daily-bar, long-only, bullish continuation only):
  1. Trend filter: close > SMA(trend_window) defines an established
     uptrend (source's own higher-timeframe trend confirmation step).
  2. Ledge detection: within a trailing `ledge_max_bars`-bar window,
     find the two highest closes/highs that are within `match_tolerance`
     of each other (the "two matching highs"), and separately the two
     lowest lows that are within `match_tolerance` of each other (the
     "two matching lows"). If both pairs exist inside the same
     `ledge_max_bars` window, a Ledge is confirmed, with ledge_high = the
     matched-highs level and ledge_low = the matched-lows level.
  3. Entry: while in an uptrend (Step 1) and a confirmed Ledge exists,
     enter long on the first bar the close breaks above ledge_high (the
     breakout in the direction of the trend, per source's explicit rule
     -- never trades the breakout against the trend).
  4. Exit: close falls back below ledge_low (failed breakout / stop), OR
     trend filter breaks (close < SMA(trend_window)), OR a
     max_hold_days time-stop, whichever comes first.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _detect_ledge(
    high: np.ndarray,
    low: np.ndarray,
    i: int,
    ledge_max_bars: int,
    match_tolerance: float,
):
    """Look at the trailing window ending at bar i (inclusive) for a Ledge:
    two matching highs and two matching lows within `ledge_max_bars` bars.
    Returns (ledge_high, ledge_low) or None."""
    start = max(0, i - ledge_max_bars + 1)
    window_high = high[start:i + 1]
    window_low = low[start:i + 1]
    if len(window_high) < 4:
        return None

    # Find the two highest highs; check if they're close to each other.
    sorted_high_idx = np.argsort(window_high)[::-1]
    h1 = window_high[sorted_high_idx[0]]
    h2 = window_high[sorted_high_idx[1]]
    if h1 == 0:
        return None
    if abs(h1 - h2) / h1 > match_tolerance:
        return None

    sorted_low_idx = np.argsort(window_low)
    l1 = window_low[sorted_low_idx[0]]
    l2 = window_low[sorted_low_idx[1]]
    if l1 == 0:
        return None
    if abs(l1 - l2) / l1 > match_tolerance:
        return None

    ledge_high = (h1 + h2) / 2.0
    ledge_low = (l1 + l2) / 2.0
    if ledge_high <= ledge_low:
        return None
    return ledge_high, ledge_low


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    ledge_max_bars: int = 10,
    match_tolerance: float = 0.01,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series for bullish Ledge breakouts."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()

    sma = close.rolling(trend_window).mean()
    uptrend = (close > sma).to_numpy()
    c_arr = close.to_numpy()
    n = len(df)

    position = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    stop_price = 0.0

    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = (
                c_arr[i] < stop_price
                or not bool(uptrend[i])
                or hold_count >= max_hold_days
            )
            if exit_now:
                in_pos = False
                hold_count = 0
            else:
                position.iloc[i] = 1.0
                continue

        if not in_pos and bool(uptrend[i]) and i >= ledge_max_bars:
            ledge = _detect_ledge(high, low, i - 1, ledge_max_bars, match_tolerance)
            if ledge is not None:
                ledge_high, ledge_low = ledge
                if c_arr[i] > ledge_high:
                    in_pos = True
                    hold_count = 0
                    stop_price = ledge_low
                    position.iloc[i] = 1.0

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

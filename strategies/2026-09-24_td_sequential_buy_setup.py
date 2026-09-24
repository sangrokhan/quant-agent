"""Strategy: TD Sequential (Tom DeMark) bullish 9-count Setup reversal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-XXX):
Per https://trendspider.com/learning-center/td-sequential-a-comprehensive-guide-for-traders/
(browser_exec; web_extract failed -- ddgs backend search-only): "TD Setup
phase consists of a 9-candle count. In a bearish trend, a starting number
'1' is plotted if a candle closes lower than the close of a candle four
periods ago. The following numbers are plotted when each successive
candle satisfies the four-period rule. The potential reversal point comes
when the TD Sequential plots the number '9' ... at the bottom of a candle
in a bearish trend. The TD Setup is immediately canceled if, at any point,
a candle fails to satisfy the four-period rule."

This strategy implements ONLY the bullish reversal signal from a
completed bearish 9-count Setup (i.e. long entry on a TD Buy Setup
completion) -- the simpler, well-documented "Setup" phase, not the more
complex 13-bar "Countdown" phase (which requires non-consecutive bar
counting and price-range comparisons not fully disclosed with exact
numeric rules in the source). First TD Sequential/DeMark strategy in this
repo (0 prior index hits) -- a genuinely distinct construction from all
prior strategies: consecutive-count-based (not moving-average/oscillator-
based), requiring an UNBROKEN streak of 9 closes each below the close
4 bars earlier.

Signal logic
------------
- bearish_count[t] = close[t] < close[t-4]; increments a running counter
  that resets to 0 the moment a bar fails the condition (immediate
  cancellation per DeMark's rule).
- Entry (long): bearish_count reaches exactly `setup_count` (default 9)
  -- i.e. a completed TD Buy Setup, an exhausted-downtrend reversal signal.
- Exit: close crosses back above the high of the setup's completion bar
  by more than a small buffer (thesis confirmed and momentum extends), OR
  close falls back below the setup completion bar's low (thesis failed,
  stop out), OR after max_hold_days.
- Flat otherwise.

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


def generate_signals(
    price_df: pd.DataFrame,
    setup_count: int = 9,
    stop_buffer_pct: float = 0.01,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    close_arr = close.to_numpy()
    low_arr = low.to_numpy()
    n = len(close_arr)

    # Track the running bearish-close-streak count (TD Buy Setup counter).
    counts = [0] * n
    running = 0
    for i in range(n):
        if i < 4:
            running = 0
        elif close_arr[i] < close_arr[i - 4]:
            running += 1
        else:
            running = 0
        counts[i] = running

    setup_complete = [c == setup_count for c in counts]

    position = pd.Series(0, index=close.index, dtype=int)
    pos_arr = position.to_numpy().copy()

    in_position = False
    hold_days = 0
    setup_low = None
    setup_high = None
    for i in range(n):
        if in_position:
            hold_days += 1
            broke_low = close_arr[i] < setup_low
            broke_high = close_arr[i] > setup_high * (1 + stop_buffer_pct)
            if broke_low or broke_high or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                setup_low, setup_high = None, None
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if setup_complete[i]:
                in_position = True
                hold_days = 0
                setup_low = low_arr[i]
                setup_high = close_arr[i]
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    position = pd.Series(pos_arr, index=close.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    setup_count: int = 9,
    stop_buffer_pct: float = 0.01,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df, setup_count=setup_count, stop_buffer_pct=stop_buffer_pct, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    strat_ret = strat_ret.fillna(0.0)
    return strat_ret

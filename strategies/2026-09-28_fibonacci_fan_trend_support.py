"""Strategy: Fibonacci Fan diagonal trendline breakout/support, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-28-XXX),
sourced from https://www.investopedia.com/terms/f/fibonaccifan.asp (James
Chen, Investopedia, read via browser_exec this iteration -- web_extract's
ddgs backend is search-only and cannot extract URL content).

Concrete mechanical rule from the source: a Fibonacci fan is constructed by
first drawing a base trendline connecting a swing low and swing high over a
given period, then drawing three additional DIAGONAL trendlines from the
same swing-low origin through the 23.6%, 38.2%, 50%, and 61.8% Fibonacci
retracement price levels (measured vertically at the swing-high's time
position). Traders use these diagonal lines as dynamic (time-varying)
support/resistance -- price reversals are expected to occur near these
fan lines, distinct from this repo's already-tested Fibonacci Retracement
strategy (2026-09-03-022, id in strategies/2026-09-03_fibonacci_retracement_pullback.py)
which uses static HORIZONTAL retracement levels of a single completed
swing. The fan lines instead extrapolate forward in time with a slope
proportional to each Fibonacci ratio, so "support/resistance" is a moving
target rather than a fixed price.

Signal logic (daily bars, causal/no look-ahead):
1. Trend filter: close > SMA(trend_window) (default 200d) -- only trade
   fan breakouts in an established uptrend, matching this repo's
   consistently-validated trend-filter AND-gate pattern used across many
   prior entries.
2. Rolling `swing_lookback`-day window: identify the swing low (price +
   its position/time index) and the swing high within that same window
   (only fan constructions where the low occurs before the high are valid
   -- an "uptrend impulse leg" -- matching the source's own upward-trend
   example).
3. For a given ratio r in {0.236, 0.382, 0.5, 0.618}, the fan line's price
   at the CURRENT bar (t, which may be beyond t_high) is:
       fan_price(r, t) = low_price + r * (high_price - low_price)
                          * (t - t_low) / (t_high - t_low)
   i.e. a line from (t_low, low_price) with slope scaled by r, matching the
   source's "trendlines...through a set of points dictated by Fibonacci
   retracements" (diagonal, not horizontal).
4. Entry (long): close crosses ABOVE the upper fan line (ratio=upper_ratio,
   default 0.618 -- the strongest resistance fan per the source) AND the
   uptrend filter holds -- a confirmed breakout through fan resistance,
   continuing the trend rather than reversing at it.
5. Exit: close crosses back BELOW the lower fan line (ratio=lower_ratio,
   default 0.382 -- the fan line degrades into support after breakout, and
   losing it signals the breakout failed) OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
validation/grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def _fan_lines(
    close: pd.Series,
    swing_lookback: int,
    upper_ratio: float,
    lower_ratio: float,
) -> tuple[pd.Series, pd.Series]:
    """Rolling causal computation of the two fan lines' current-bar price.

    For each bar t, look back `swing_lookback` bars (inclusive of t) to find
    the swing low (min close, at position idx_low within the window) and
    the swing high AFTER that low (max close among bars from idx_low
    onward). Only accept a valid fan (idx_low < idx_high, idx_high < last
    position in window so it's a genuinely completed impulse leg) --
    otherwise NaN (no fan defined yet).
    """
    n = len(close)
    upper_line = pd.Series(np.nan, index=close.index)
    lower_line = pd.Series(np.nan, index=close.index)
    values = close.values

    for t in range(n):
        start = max(0, t - swing_lookback + 1)
        window = values[start : t + 1]
        if len(window) < 5:
            continue
        idx_low_rel = int(np.argmin(window))
        # swing high must occur strictly after the swing low within the window
        if idx_low_rel >= len(window) - 2:
            continue
        sub_after_low = window[idx_low_rel:]
        idx_high_rel = idx_low_rel + int(np.argmax(sub_after_low))
        if idx_high_rel == idx_low_rel or idx_high_rel >= len(window) - 1:
            # need the high to be strictly before the current bar so we can
            # extrapolate the fan forward at least one bar
            continue

        low_price = window[idx_low_rel]
        high_price = window[idx_high_rel]
        if high_price <= low_price:
            continue

        t_low = start + idx_low_rel
        t_high = start + idx_high_rel
        dt_total = t_high - t_low
        if dt_total <= 0:
            continue

        dt_current = t - t_low
        slope_unit = (high_price - low_price) / dt_total

        upper_line.iloc[t] = low_price + upper_ratio * slope_unit * dt_current
        lower_line.iloc[t] = low_price + lower_ratio * slope_unit * dt_current

    return upper_line, lower_line


def generate_signals(
    price_df: pd.DataFrame,
    swing_lookback: int = 60,
    trend_window: int = 200,
    upper_ratio: float = 0.618,
    lower_ratio: float = 0.382,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    upper_line, lower_line = _fan_lines(close, swing_lookback, upper_ratio, lower_ratio)

    prev_close = close.shift(1)
    prev_upper = upper_line.shift(1)
    prev_lower = lower_line.shift(1)

    cross_above_upper = (prev_close <= prev_upper) & (close > upper_line)
    cross_below_lower = (prev_close >= prev_lower) & (close < lower_line)

    entry = cross_above_upper.fillna(False) & uptrend.fillna(False)
    exit_signal = cross_below_lower.fillna(False)

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

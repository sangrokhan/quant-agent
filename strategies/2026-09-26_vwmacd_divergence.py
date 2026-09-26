"""Strategy: Volume-Weighted MACD (VW-MACD) price/indicator divergence.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-065):
Per Google AI-overview synthesis (browser_exec Google SERP; underlying
sources cited: LuxAlgo, Evest, "Quant Tactics", "CodeTrading" -- consistent
across multiple independent write-ups for this query, so treated as a
reliable summary of a commonly-taught rule rather than a single unverified
blog): a Volume-Weighted MACD DIVERGENCE strategy, distinct from the
signal-line-crossover VW-MACD variants already in this repo
(2026-09-04-142/2026-09-06-113/2026-09-18-061/2026-09-18-062, all triggered
purely on VW-MACD-line-vs-signal-line crosses) and the histogram
continuous-sizing variant (2026-09-14-155/2026-09-15-004, a z-scored
magnitude dial, not a divergence pattern). This construction instead
compares PRICE swing structure against VW-MACD-line swing structure:

- Bullish divergence: price makes a LOWER swing low while the VW-MACD line
  (VWMA(fast) - VWMA(slow), volume-weighted so thin/low-volume drift barely
  registers) makes a HIGHER swing low over the same window -- selling
  pressure lacks volume conviction. Trigger: enter long when VW-MACD line
  crosses back above its own signal line following the divergence pattern.
- Bearish divergence: price makes a HIGHER swing high while VW-MACD makes a
  LOWER swing high -- buying exhaustion, volume failing to keep pace.
  Trigger: exit/flatten (long-only construction, no short leg, consistent
  with this repo's other long-only VW-MACD variants) when VW-MACD crosses
  back below signal following the bearish divergence, or on a fixed
  max_hold_days time-stop.

This differs structurally from every prior VW-MACD entry in this repo: those
all fire on a bare signal-line cross (or histogram magnitude); this one
requires a genuine price-vs-indicator swing-structure disagreement over a
lookback window as a precondition before the crossover trigger is honored.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _vwma(close: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    pv = (close * volume).rolling(window).sum()
    v = volume.rolling(window).sum()
    return pv / v.replace(0, np.nan)


def _rolling_swing_low_idx(series: pd.Series, window: int) -> pd.Series:
    """Index (position) of the minimum value within the trailing `window` bars."""
    return series.rolling(window).apply(lambda x: np.argmin(x.values), raw=False)


def _rolling_swing_high_idx(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).apply(lambda x: np.argmax(x.values), raw=False)


def generate_signals(
    price_df: pd.DataFrame,
    vwmacd_fast: int = 12,
    vwmacd_slow: int = 26,
    vwmacd_signal: int = 9,
    swing_window: int = 20,
    divergence_lookback: int = 40,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Bullish divergence precondition: comparing the swing-low bar within the
    most recent `swing_window` vs the swing-low bar within the PRIOR
    `swing_window` (i.e. two consecutive non-overlapping windows spanning
    `divergence_lookback` = 2*swing_window bars total): price's later swing
    low is LOWER than its earlier swing low, while VW-MACD's later swing low
    (measured at the same price-swing-low bar positions) is HIGHER than its
    earlier swing low. Entry armed by that precondition, fires on the next
    bullish VW-MACD/signal-line crossover within `divergence_lookback` bars.
    Exit: bearish crossover, or `max_hold_days` time-stop.
    """
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    fast_vwma = _vwma(close, volume, vwmacd_fast)
    slow_vwma = _vwma(close, volume, vwmacd_slow)
    vwmacd_line = (fast_vwma - slow_vwma).astype(float)
    signal_line = vwmacd_line.ewm(span=vwmacd_signal, adjust=False).mean()

    above = vwmacd_line > signal_line
    bull_cross = above & (~above.shift(1).fillna(False))
    bear_cross = (~above) & (above.shift(1).fillna(False))

    n = len(close)
    close_v = close.to_numpy()
    macd_v = vwmacd_line.to_numpy()
    w = swing_window

    bullish_divergence_armed = np.zeros(n, dtype=bool)
    for i in range(2 * w, n):
        prev_win_close = close_v[i - 2 * w : i - w]
        curr_win_close = close_v[i - w : i]
        prev_win_macd = macd_v[i - 2 * w : i - w]
        curr_win_macd = macd_v[i - w : i]
        if np.any(np.isnan(prev_win_close)) or np.any(np.isnan(curr_win_close)):
            continue
        if np.any(np.isnan(prev_win_macd)) or np.any(np.isnan(curr_win_macd)):
            continue
        prev_low_i = int(np.argmin(prev_win_close))
        curr_low_i = int(np.argmin(curr_win_close))
        price_lower_low = curr_win_close[curr_low_i] < prev_win_close[prev_low_i]
        macd_higher_low = curr_win_macd[curr_low_i] > prev_win_macd[prev_low_i]
        bullish_divergence_armed[i] = bool(price_lower_low and macd_higher_low)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    armed_until = -1
    for i in range(n):
        if bullish_divergence_armed[i]:
            armed_until = i + divergence_lookback

        if in_position:
            held = i - entry_idx
            if bool(bear_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if i <= armed_until and bool(bull_cross.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    leverage_cap = kwargs.pop("leverage_cap", 1.0)
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret * leverage_cap
    return strategy_ret

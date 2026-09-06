"""Strategy: Detrended Price Oscillator (DPO) trough-turn cycle-timing entry.

Hypothesis (see knowledge_base id 2026-09-06-139):
Per GoCharting's DPO documentation
(https://gocharting.com/docs/charting/technical-indicator/oscillators/detrended-price-oscillator):
"Identify the dominant cycle length from historical highs and lows. Set DPO
period to half that cycle length plus one. Buy when DPO reaches a
historically significant trough and turns up; sell when it reaches a peak
and turns down." Also explicitly: "Do not use DPO to determine trend
direction... always combine with a trend filter."

This is distinct from the two prior DPO strategies already in this repo:
- 2026-09-04-056 (zero-line crossover -- a simplified proxy for the source's
  trough/peak rule, NOT the actual peak/trough-turn logic itself)
- 2026-09-05-062 (DPO + ADX/DM + Parabolic SAR triple-confirmation trend
  entry, gated on zero-cross not trough-turn)

Here we implement the *actual* trough-turn rule from the source (DPO makes
a local minimum then turns up = buy), gated by a simple trend filter (source
explicitly warns DPO alone isn't a trend indicator) using a long-term SMA
slope, rather than DPO zero-cross or a multi-indicator confirmation stack.

Signal logic
------------
- DPO = close shifted back by (dpo_window // 2 + 1) minus the simple moving
  average of `dpo_window` periods (standard non-centered/backward DPO
  formula, avoiding lookahead: uses only past closes).
- Trend filter: `trend_sma_window`-day SMA must be rising (today's SMA >
  SMA `trend_slope_lookback` days ago) -- only trade DPO troughs in an
  uptrend, per the source's explicit warning against using DPO standalone.
- Entry (long): DPO makes a local minimum over a trailing `turn_window`-bar
  window (i.e. DPO[i] is the lowest value in [i-turn_window, i]) at bar i-1,
  and DPO turns up at bar i (DPO[i] > DPO[i-1]), AND the trend filter is
  bullish.
- Exit: DPO makes a subsequent local peak-then-turn-down (symmetric logic,
  DPO[i] < DPO[i-1] after a trailing local max), OR trend filter flips
  bearish, OR `max_hold_days` time-stop.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def _dpo(close: pd.Series, dpo_window: int) -> pd.Series:
    shift = dpo_window // 2 + 1
    sma = close.rolling(dpo_window).mean()
    return close.shift(shift) - sma


def generate_signals(
    price_df: pd.DataFrame,
    dpo_window: int = 20,
    turn_window: int = 5,
    trend_sma_window: int = 50,
    trend_slope_lookback: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    dpo = _dpo(close, dpo_window)

    trend_sma = close.rolling(trend_sma_window).mean()
    trend_bullish = trend_sma > trend_sma.shift(trend_slope_lookback)

    dpo_vals = dpo.values

    is_trough_turn = pd.Series(False, index=close.index)
    is_peak_turn = pd.Series(False, index=close.index)
    for i in range(turn_window + 1, n):
        window = dpo_vals[i - turn_window : i]  # excludes current bar i
        prior = dpo_vals[i - 1]
        cur = dpo_vals[i]
        if np.isnan(window).any() or np.isnan(prior) or np.isnan(cur):
            continue
        if prior == window.min() and cur > prior:
            is_trough_turn.iloc[i] = True
        if prior == window.max() and cur < prior:
            is_peak_turn.iloc[i] = True

    entry = is_trough_turn & trend_bullish.fillna(False)
    exit_signal = is_peak_turn | (~trend_bullish.fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
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

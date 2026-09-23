"""Strategy: Chande's VIDYA (Variable Index Dynamic Average) price crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-021):
Per Google AI-overview synthesis (corroborated by StrategyQuant, ArrowAlgo,
cTrader help): Tushar Chande's VIDYA is an EMA whose smoothing constant is
scaled by the absolute value of the Chande Momentum Oscillator (CMO) --
speeding up in trending/volatile conditions and slowing down in flat/choppy
conditions. The disclosed trading rule: long entry when price (close)
crosses above the VIDYA line; exit (or short, adapted long-only here per
SAFETY.md) when price crosses below VIDYA. An advanced refinement noted by
multiple sources: ignore crossovers when the VIDYA line itself is flat
(low |slope|) to reduce whipsaw in range-bound conditions -- implemented
here as a slope-magnitude filter. First VIDYA-family strategy in this repo
(0 prior KB hits for "VIDYA").

Signal logic
------------
- CMO(cmo_period) on close (Chande Momentum Oscillator, -100..100).
- Alpha[t] = (2 / (vidya_period + 1)) * |CMO[t]| / 100 (adaptive smoothing
  constant, scaled by CMO's magnitude).
- VIDYA[t] = Alpha[t] * close[t] + (1 - Alpha[t]) * VIDYA[t-1].
- Slope filter: |VIDYA[t] - VIDYA[t - slope_window]| / VIDYA[t] must exceed
  slope_threshold for a crossover to count as a valid signal (source's own
  "ignore signals when VIDYA is flat" refinement).
- Entry (long): close crosses above VIDYA, with the slope filter active.
- Exit: close crosses below VIDYA, OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _cmo(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    sum_up = up.rolling(period).sum()
    sum_down = down.rolling(period).sum()
    denom = (sum_up + sum_down).replace(0, np.nan)
    cmo = 100.0 * (sum_up - sum_down) / denom
    return cmo.fillna(0.0)


def _vidya(close: pd.Series, vidya_period: int, cmo_period: int) -> pd.Series:
    cmo = _cmo(close, cmo_period)
    alpha = (2.0 / (vidya_period + 1.0)) * (cmo.abs() / 100.0)
    alpha = alpha.fillna(0.0)

    close_vals = close.values
    alpha_vals = alpha.values
    n = len(close_vals)
    vidya = np.zeros(n)
    vidya[0] = close_vals[0]
    for i in range(1, n):
        a = alpha_vals[i]
        vidya[i] = a * close_vals[i] + (1.0 - a) * vidya[i - 1]
    return pd.Series(vidya, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    vidya_period: int = 14,
    cmo_period: int = 9,
    slope_window: int = 5,
    slope_threshold: float = 0.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    vidya = _vidya(close, vidya_period, cmo_period)
    slope = (vidya - vidya.shift(slope_window)).abs() / vidya.replace(0, np.nan).abs()
    slope_ok = slope.fillna(0.0) > slope_threshold

    above = close > vidya
    prev_above = above.shift(1).fillna(False)
    cross_up = above & (~prev_above) & slope_ok

    below = close < vidya
    prev_below = below.shift(1).fillna(True)
    cross_down = below & (~prev_below)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
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

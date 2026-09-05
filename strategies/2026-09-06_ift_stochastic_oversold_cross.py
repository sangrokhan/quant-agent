"""Strategy: Ehlers Inverse Fisher Transform of the Stochastic Oscillator.

Hypothesis (see knowledge_base/strategies_log.jsonl):
John Ehlers' Inverse Fisher Transform (IFT), when applied to a smoothed
Stochastic %K reading, compresses the oscillator's most probable values
toward the extremes (-1/+1) and sharpens the near-zero/near-boundary
transition into a squarer, more decisive digital-like signal, unlike the
raw Stochastic's smooth analog wandering. Per thinkorswim's IFT_StochOsc
study documentation (https://toslc.thinkorswim.com/center/reference/Tech-Indicators/studies-library/G-L/IFT-StochOsc,
crediting Sylvain Vervoort's TASC Dec 2011 article): "the IFT Stochastic
Oscillator ... combines Inverse Fisher Transform (IFT) and Stochastic
approaches ... use the IFT plot in combination with auxiliary overbought
and oversold levels" to find buying/selling opportunities. Ehlers' own
canonical formula (widely reproduced, e.g. "Using The Fisher Transform",
Stocks & Commodities): v1 = 0.1*(Stochastic%K - 50), v2 = smoothed(v1),
IFT = (exp(2*v2)-1)/(exp(2*v2)+1). Because the IFT squares off the
transition, a cross above a negative threshold (e.g. -0.5) after being
oversold is a sharper/earlier reversal signal than waiting for the raw
Stochastic to cross 20/30.

First Inverse-Fisher-Transform-of-Stochastic strategy in this repo --
distinct from the already-tested plain (forward) Fisher Transform of PRICE
(2026-09-04-051, 2026-09-05-086) since this is the INVERSE transform
applied to a different underlying series (the Stochastic oscillator, not
price itself) -- mathematically a different construction (IFT compresses
toward +/-1 saturating extremes; the forward Fisher Transform expands
toward a Gaussian).

Signal logic
------------
- Stochastic %K over `stoch_window`, smoothed by an SMA of `smooth_k`
  (reduces raw whipsaw before the transform, per the source's "rainbow
  averaging" rationale).
- v1 = 0.1 * (Stochastic - 50)  (rescale 0-100 to roughly -5..+5)
- v2 = EMA(v1, `ift_smooth`)     (additional smoothing before the transform)
- IFT = (exp(2*v2) - 1) / (exp(2*v2) + 1)   (squashes to [-1, +1])
- Long entry: IFT crosses above `entry_threshold` (default -0.5) while
  having recently been below it (oversold-recovery cross).
- Exit: IFT crosses back below `exit_threshold` (default 0.5, i.e. leaving
  overbought), or a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _ift_stoch(df: pd.DataFrame, stoch_window: int, smooth_k: int, ift_smooth: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    lowest_low = low.rolling(stoch_window).min()
    highest_high = high.rolling(stoch_window).max()
    raw_k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    smoothed_k = raw_k.rolling(smooth_k).mean()

    v1 = 0.1 * (smoothed_k - 50)
    v2 = v1.ewm(span=ift_smooth, adjust=False).mean()
    ift = (np.exp(2 * v2) - 1) / (np.exp(2 * v2) + 1)
    return ift


def generate_signals(
    price_df: pd.DataFrame,
    stoch_window: int = 13,
    smooth_k: int = 3,
    ift_smooth: int = 5,
    entry_threshold: float = -0.5,
    exit_threshold: float = 0.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    ift = _ift_stoch(df, stoch_window, smooth_k, ift_smooth)

    long_trigger = (ift > entry_threshold) & (ift.shift(1) <= entry_threshold)
    exit_trigger = (ift < exit_threshold) & (ift.shift(1) >= exit_threshold)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(df)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(long_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    position.name = "position"
    return position


def generate_returns(
    price_df: pd.DataFrame,
    stoch_window: int = 13,
    smooth_k: int = 3,
    ift_smooth: int = 5,
    entry_threshold: float = -0.5,
    exit_threshold: float = 0.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df, stoch_window=stoch_window, smooth_k=smooth_k, ift_smooth=ift_smooth,
        entry_threshold=entry_threshold, exit_threshold=exit_threshold,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns

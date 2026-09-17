"""Strategy: Ehlers Fisherized Deviation-Scaled Oscillator (FDSO) mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-154):
John Ehlers' Traders' Tips article "Probability -- Probably A Good Thing To
Know" (TASC Oct 2018, source: Traders.com Oct 2018 Traders' Tips, TradeStation
EasyLanguage code read this iteration) proposes a SuperSmoother-filtered,
RMS-normalized, Fisher-transformed oscillator (FDSO) whose Fisher Transform
step forces an approximately-Gaussian probability distribution on the raw
scaled filter output -- making fixed overbought/oversold thresholds (+-2)
statistically meaningful cutoffs for mean-reversion entries/exits, unlike an
arbitrary raw-indicator threshold. This repo already has a DSO zero-line
crossover strategy (2026-09-11-128, distinct: no Fisher transform, EMA trend
confluence gate, not a mean-reversion oscillator-band strategy) -- this is
the first *Fisher-transformed* oscillator-band mean-reversion strategy here.

Signal logic (long-only adaptation of the TradeStation strategy, which is
long/short in the original)
------------------------------------------------------------------------
- Zeros = Close - Close.shift(2) (2-bar momentum, removes DC and Nyquist).
- 2-pole SuperSmoother low-pass filter of Zeros (Ehlers standard formula,
  pole angle derived from `period`).
- RMS = sqrt(mean(Filt^2) over trailing `period` bars).
- ScaledFilt = Filt / RMS (bounded volatility-normalized oscillator).
- FisherFilt = 0.5 * ln((1+ScaledFilt/2)/(1-ScaledFilt/2)), only defined
  where |ScaledFilt| < 2 (else carry forward previous value).
- Entry (long): FisherFilt crosses above `oversold` (-2 in the original;
  kept as a tunable parameter here since our normalized scale may differ
  slightly in magnitude from TradeStation's).
- Exit: FisherFilt crosses below 0 (mean reached), OR after `max_hold_days`
  (avoid indefinite holds; the original strategy has no time stop, added
  here for research-loop consistency with other strategies in this repo).
- No short leg (repo convention: long/flat only).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fisherized_dso(close: pd.Series, period: int) -> pd.Series:
    n = len(close)
    zeros = close.values - np.roll(close.values, 2)
    zeros[:2] = 0.0

    a1 = math.exp(-1.414 * math.pi / (0.5 * period))
    b1 = 2 * a1 * math.cos(1.414 * math.pi / (0.5 * period))
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    filt = np.zeros(n)
    for i in range(n):
        z_i = zeros[i]
        z_im1 = zeros[i - 1] if i >= 1 else 0.0
        f_im1 = filt[i - 1] if i >= 1 else 0.0
        f_im2 = filt[i - 2] if i >= 2 else 0.0
        filt[i] = c1 * (z_i + z_im1) / 2 + c2 * f_im1 + c3 * f_im2

    rms = np.zeros(n)
    for i in range(n):
        lo = max(0, i - period + 1)
        window = filt[lo : i + 1]
        rms[i] = math.sqrt(np.mean(window ** 2)) if len(window) > 0 else 0.0

    scaled_filt = np.where(rms != 0, filt / np.where(rms == 0, 1, rms), 0.0)

    fisher = np.zeros(n)
    for i in range(n):
        sf = scaled_filt[i]
        if abs(sf) < 2:
            fisher[i] = 0.5 * math.log((1 + sf / 2) / (1 - sf / 2))
        else:
            fisher[i] = fisher[i - 1] if i >= 1 else 0.0

    return pd.Series(fisher, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 40,
    oversold: float = -2.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fisher = _fisherized_dso(close, period)

    cross_above_oversold = (fisher.shift(1) <= oversold) & (fisher > oversold)
    cross_below_zero = (fisher.shift(1) >= 0) & (fisher < 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if i < period:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(cross_below_zero.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_above_oversold.iloc[i]):
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

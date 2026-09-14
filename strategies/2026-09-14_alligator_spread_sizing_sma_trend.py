"""Strategy: SMA(trend_window) directional gate with continuous Williams
Alligator (Bill Williams, 1995) fan-spread sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
This repo's Williams Alligator entries (2026-09-04-112 crossover, ACCEPTED;
2026-09-05-050 Gator Oscillator wake-up, 2026-09-09-071 eating-state
pullback) are all binary trigger/state-machine rules. This iteration
reframes the Alligator's own signed fan-spread (Lips - Jaw, the widest
pairwise gap between the three SMMA lines, positive when bullishly fanned
lips>jaw and negative when bearishly inverted) as a CONTINUOUS SIZING dial:
normalized by rolling ATR (so the spread magnitude is comparable across
regimes) then tanh-squashed to [-1,+1], within an SMA(trend_window)
uptrend gate. First Alligator-as-continuous-sizing-dial variant.

Source: same Alligator SMMA/shift construction as this repo's own
2026-09-04-112 (https://howtotrade.com/indicators/alligator-indicator/,
re-confirmed via this repo's own prior implementation, no new external
fetch needed this iteration).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _smma(series: pd.Series, period: int) -> pd.Series:
    """Wilder/Williams smoothed moving average: seed with SMA(period), then
    smma[t] = (smma[t-1]*(period-1) + price[t]) / period."""
    sma_seed = series.rolling(period).mean()
    seeded = False
    vals = series.values
    out = [float("nan")] * len(series)
    for i in range(len(series)):
        if not seeded:
            if i >= period - 1:
                out[i] = sma_seed.iloc[i]
                seeded = True
        else:
            out[i] = (out[i - 1] * (period - 1) + vals[i]) / period
    return pd.Series(out, index=series.index)


def _alligator_spread(
    df: pd.DataFrame,
    jaw_period: int,
    jaw_shift: int,
    lips_period: int,
    lips_shift: int,
    atr_window: int,
) -> pd.Series:
    median_price = (df["high"] + df["low"]) / 2.0
    jaw = _smma(median_price, jaw_period).shift(jaw_shift)
    lips = _smma(median_price, lips_period).shift(lips_shift)

    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(atr_window).mean().replace(0.0, np.nan)

    spread = (lips - jaw) / atr
    return spread.fillna(0.0)


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    jaw_period: int = 13,
    jaw_shift: int = 8,
    lips_period: int = 5,
    lips_shift: int = 3,
    atr_window: int = 14,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Alligator ATR-normalized Lips-Jaw spread is tanh-squashed to [-1,+1],
    then used as a sizing dial within the SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    spread = _alligator_spread(df, jaw_period, jaw_shift, lips_period, lips_shift, atr_window)
    dial = np.tanh(spread)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    jaw_period: int = 13,
    jaw_shift: int = 8,
    lips_period: int = 5,
    lips_shift: int = 3,
    atr_window: int = 14,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        jaw_period=jaw_period,
        jaw_shift=jaw_shift,
        lips_period=lips_period,
        lips_shift=lips_shift,
        atr_window=atr_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

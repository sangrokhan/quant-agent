"""Strategy: SMA(trend_window) directional gate with continuous Trend
Magic (Kivanc Ozbilgic) distance-from-line sizing overlay + deadband,
leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-16-053, this cron trigger):
Trend Magic (Kivanc Ozbilgic, MT4/TradingView indicator), per Google search
results reading an EzAlgo Pine Script snippet (Scribd) and corroborating
GitHub source, visited this iteration via browser_exec Google fallback:
upT = low - ATR(atr_period)*coeff; downT = high + ATR(atr_period)*coeff.
The "Magic Trend" line itself is a ratcheting trailing-stop line whose
DIRECTION is decided by CCI(cci_period) sign (not by price crossing the
line, unlike Chandelier Exit/SuperTrend/PSAR/HalfTrend already tested in
this repo): when CCI>=0 the line ratchets up as max(prior_line, upT)
(support in an uptrend); when CCI<0 it ratchets down as
min(prior_line, downT) (resistance in a downtrend). First strategy in this
repo to gate an ATR trailing-stop-style ratcheting line's direction by an
oscillator's SIGN rather than a price-crossing event -- distinct
construction from every prior Chandelier/SuperTrend/PSAR/HalfTrend/Gann
HiLo trailing-line strategy in this repo.

Construction (continuous sizing dial, following this repo's established
distance-from-a-reference-line pattern): percent-distance of close from
the Trend Magic line, rolling z-scored and tanh-squashed into [-1,+1],
used as a continuous exposure-sizing dial inside an SMA(trend_window)
uptrend gate with a deadband to cut turnover.

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


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    prior_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prior_close).abs(),
            (low - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _cci(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    tp = (high + low + close) / 3.0
    sma_tp = tp.rolling(window).mean()
    mad = tp.rolling(window).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - sma_tp) / (0.015 * mad.replace(0.0, np.nan))


def _trend_magic_line(
    high: pd.Series, low: pd.Series, close: pd.Series,
    atr_period: int, atr_coeff: float, cci_period: int,
) -> pd.Series:
    """Ratcheting trailing line: direction decided by CCI sign, not by
    price crossing the line (distinct from Chandelier/SuperTrend/PSAR).
    """
    atr = _atr(high, low, close, atr_period)
    cci = _cci(high, low, close, cci_period)
    up_t = low - atr * atr_coeff
    down_t = high + atr * atr_coeff

    line = np.full(len(close), np.nan)
    prev = 0.0
    for i in range(len(close)):
        if pd.isna(up_t.iloc[i]) or pd.isna(down_t.iloc[i]) or pd.isna(cci.iloc[i]):
            line[i] = prev
            continue
        if cci.iloc[i] >= 0:
            prev = max(prev, up_t.iloc[i])
        else:
            prev = min(prev, down_t.iloc[i]) if prev != 0.0 else down_t.iloc[i]
        line[i] = prev
    return pd.Series(line, index=close.index)


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
    atr_period: int = 5,
    atr_coeff: float = 1.0,
    cci_period: int = 20,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Percent-distance of close from the Trend Magic line is rolling
    z-scored over `zscore_window` and tanh-squashed to [-1,+1] before use
    as a sizing dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    line = _trend_magic_line(high, low, close, atr_period, atr_coeff, cci_period)
    pct_dist = (close - line) / line.replace(0.0, np.nan)

    roll_mean = pct_dist.rolling(zscore_window).mean()
    roll_std = pct_dist.rolling(zscore_window).std()
    zscore = (pct_dist - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    atr_period: int = 5,
    atr_coeff: float = 1.0,
    cci_period: int = 20,
    zscore_window: int = 100,
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
        atr_period=atr_period,
        atr_coeff=atr_coeff,
        cci_period=cci_period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

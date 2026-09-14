"""Strategy: SMA(trend_window) directional gate with continuous Rahul
Mohindar Oscillator (RMO) ST2-ST3 swing-line-diff sizing overlay +
deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Rahul Mohindar Oscillator (Viratech India, official MetaStock inclusion
2006): MA_1 = SMA(close, sma_period); MA_k = SMA(MA_{k-1}, sma_period) for
k=2..10 (10 chained SMAs); RMO = close - MA_10 (long-term trend-bias
line); ST2 = EMA(RMO, st2_span); ST3 = EMA(ST2, st3_span) (medium/slow
swing timing lines). Formula reused from repo's own already-confirmed
implementation (strategies/2026-09-05_rmo_swingline_regime_crossover.py,
sourced from trendsandbreakouts.com's RMO guide). Repo has 1 prior RMO
entry, a binary ST2/ST3-crossover-within-RMO-zero-line-regime trigger
(accepted QQQ only, SPY near-miss, crypto decisively rejected). This
iteration reframes the ST2-ST3 swing-line spread (already roughly
zero-centered by construction, since both are EMA-smoothings of a
zero-centered RMO line) as a CONTINUOUS SIZING dial: rolling z-scored +
tanh-squashed to [-1,1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate, deadband to cut turnover, leverage_cap for
crypto. First RMO continuous-sizing variant in this repo.

Source: repo's own prior confirmed formula (2026-09-05-004,
trendsandbreakouts.com); this iteration reuses the confirmed formula and
only changes how the indicator's output is consumed (continuous sizing
dial instead of a discrete swing-line crossover).

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


def _rmo_lines(close: pd.Series, sma_period: int, st2_span: int, st3_span: int):
    ma = close
    for _ in range(10):
        ma = ma.rolling(sma_period, min_periods=max(2, sma_period // 2)).mean()
    rmo = close - ma
    st2 = rmo.ewm(span=st2_span, adjust=False).mean()
    st3 = st2.ewm(span=st3_span, adjust=False).mean()
    return rmo, st2, st3


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
    sma_period: int = 2,
    st2_span: int = 30,
    st3_span: int = 30,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    RMO's ST2-ST3 swing-line spread (already roughly zero-centered) is
    rolling z-scored over `zscore_window` bars and tanh-squashed to [-1,+1]
    before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    _, st2, st3 = _rmo_lines(close, sma_period, st2_span, st3_span)
    diff = st2 - st3

    roll_mean = diff.rolling(zscore_window).mean()
    roll_std = diff.rolling(zscore_window).std()
    zscore = (diff - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    sma_period: int = 2,
    st2_span: int = 30,
    st3_span: int = 30,
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
        sma_period=sma_period,
        st2_span=st2_span,
        st3_span=st3_span,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

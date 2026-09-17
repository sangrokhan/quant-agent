"""Strategy: Vote-K=2 4-Signal Regime Filter (precise thresholds), trend
gate reframed for un-leveraged QQQ.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-006):
Direct refinement of this cron trigger's own id=2026-09-18-005 (Quad-Signal
Risk-On Regime Vote), now using the EXACT numeric signal thresholds
disclosed in a follow-up r/LETFs post from the same author
("40-year LETF rotation backtest — 5 strategy families, 426 configs",
https://www.reddit.com/r/LETFs/comments/1t7q8or/, read via browser_exec
this iteration): the winning "Vote-K=2" config holds QLD (2x NDX) when at
least 2 of 4 signals are TRUE on the QQQ underlying -- price > SMA(250),
price > SMA(100), realized_vol(21d) < 40% (ABSOLUTE annualized threshold,
not relative-to-median as this cron trigger's own prior 2026-09-18-005
approximation used), AR(1) coefficient over a 30-day window > 0 (a genuine
lag-1 autocorrelation coefficient of daily returns, distinct from
2026-09-18-005's simpler 20-day-return-positive persistence proxy) --
else hold ZROZ (25y zero-coupon Treasury, held flat here). This iteration
tests the PRECISE disclosed thresholds (250/100-day SMAs, 40% absolute vol
cap, true AR(1) coefficient) against the un-leveraged QQQ, distinct enough
from 2026-09-18-005's simpler approximated signal definitions to be a
genuine follow-up test rather than a duplicate.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series).
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


def _rolling_ar1(returns: pd.Series, window: int) -> pd.Series:
    """Rolling lag-1 autocorrelation coefficient of daily returns."""
    r = returns.to_numpy()
    n = len(r)
    out = np.full(n, np.nan)
    for i in range(window, n):
        seg = r[i - window : i]
        x0 = seg[:-1]
        x1 = seg[1:]
        if len(x0) < 3 or np.std(x0) == 0 or np.std(x1) == 0:
            out[i] = 0.0
            continue
        out[i] = np.corrcoef(x0, x1)[0, 1]
    return pd.Series(out, index=returns.index)


def generate_signals(
    price_df: pd.DataFrame,
    sma_long: int = 250,
    sma_medium: int = 100,
    vol_window: int = 21,
    vol_threshold: float = 0.40,
    ar1_window: int = 30,
    vote_threshold: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series (>=vote_threshold of 4
    regime signals must agree for a long position)."""
    df = _prep(price_df)
    close = df["close"]

    signal_trend_long = close > close.rolling(sma_long).mean()
    signal_trend_medium = close > close.rolling(sma_medium).mean()

    daily_log_ret = (close / close.shift(1)).apply(
        lambda r: math.log(r) if r and r > 0 else None
    ).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    signal_low_vol = realized_vol < vol_threshold

    daily_ret = close.pct_change()
    ar1 = _rolling_ar1(daily_ret, ar1_window)
    signal_ar1_positive = ar1 > 0

    votes = (
        signal_trend_long.fillna(False).astype(int)
        + signal_trend_medium.fillna(False).astype(int)
        + signal_low_vol.fillna(False).astype(int)
        + signal_ar1_positive.fillna(False).astype(int)
    )

    position = (votes >= vote_threshold).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

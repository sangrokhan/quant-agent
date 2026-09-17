"""Strategy: Vote-K=2 4-Signal Regime Filter WITH 5% SMA whipsaw buffer.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-007):
Direct follow-up to this cron trigger's own id 2026-09-18-006 (Vote-K=2
precise 4-signal regime filter without a buffer). The SAME r/LETFs source
post ("40-year LETF rotation backtest", Tier 3 winner description,
https://www.reddit.com/r/LETFs/comments/1t7q8or/) explicitly specifies
that its actual winning config uses a 5% BUFFER on both SMA-based signals
("price > SMA(250) with 5% buffer (whipsaw filter)"; "price > SMA(100)
with 5% buffer") -- i.e. the trend signal only flips TRUE when price is
more than 5% above the SMA (not merely crossing it), reducing whipsaw
trade count by the source's own claimed ~30%. This iteration adds that
buffer to 2026-09-18-006's construction: signal_trend_long = close >
sma_long*(1+buffer); signal_trend_medium = close > sma_medium*(1+buffer);
same realized_vol(21d)<vol_threshold and AR(1)>0 signals, same
vote_threshold=2-of-4 gate. Distinct enough from 2026-09-18-006 (a
meaningfully different trend-signal definition, not just a param retune)
to log as its own novelty-checked iteration per Step 3 of RESEARCH_LOOP.md.

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
    sma_buffer: float = 0.05,
    vol_window: int = 21,
    vol_threshold: float = 0.40,
    ar1_window: int = 30,
    vote_threshold: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series (>=vote_threshold of 4
    regime signals must agree for a long position). SMA-based signals
    require price to exceed the SMA by `sma_buffer` (e.g. 0.05 = 5%) to
    reduce whipsaw, per the source's own disclosed construction.
    """
    df = _prep(price_df)
    close = df["close"]

    sma_long_line = close.rolling(sma_long).mean()
    sma_medium_line = close.rolling(sma_medium).mean()
    signal_trend_long = close > sma_long_line * (1.0 + sma_buffer)
    signal_trend_medium = close > sma_medium_line * (1.0 + sma_buffer)

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

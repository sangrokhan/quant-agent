"""Strategy: Bollinger Bandwidth-percentile squeeze breakout (no Keltner
Channel), gated by an SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-020):
Per quantifiedstrategies.com's Bollinger Band Squeeze article, Bollinger
Bandwidth (BW = (upper_band - lower_band) / basis_sma) contracting to a
rolling N-day low identifies a volatility-compression "squeeze" that often
precedes a strong directional breakout. The source's own numeric backtest
rule is paywalled and their own PEP example underperformed buy-and-hold, but
the underlying bandwidth-percentile-squeeze + breakout-continuation concept
is disclosed free -- operationalized here as a testable mechanical rule:
squeeze state = bandwidth is at/below its own `squeeze_percentile`
trailing-`bw_lookback`-day quantile; entry = a squeeze occurred within the
last `squeeze_recency` bars AND close breaks above the upper Bollinger Band
(the breakout), gated by close > SMA(trend_window) to avoid false breakouts
in downtrends; exit on close crossing back below the basis SMA (mean
reversion / momentum failure) or a max_hold_days time-stop.

Distinct from prior Keltner-Channel-based squeeze strategies in this repo
(TTM Squeeze id=2026-09-04-091, LazyBear Squeeze Momentum id=2026-09-04-126)
-- this uses PURE Bollinger Bandwidth percentile-rank as the squeeze
detector (no Keltner Channel comparison at all), a structurally simpler and
distinct construction per the source's own approach.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    bw_lookback: int = 100,
    squeeze_percentile: float = 0.2,
    squeeze_recency: int = 5,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    upper_band = sma + bb_std * std
    lower_band = sma - bb_std * std
    bandwidth = (upper_band - lower_band) / sma

    bw_rank = bandwidth.rolling(bw_lookback).apply(
        lambda x: (x.iloc[-1] <= x).mean() if len(x.dropna()) else float("nan"),
        raw=False,
    )
    in_squeeze = bw_rank <= squeeze_percentile
    recent_squeeze = in_squeeze.rolling(squeeze_recency, min_periods=1).max().astype(bool)

    breakout = close > upper_band
    sma_trend = close.rolling(trend_window).mean()
    trend_ok = close > sma_trend

    entry = (recent_squeeze & breakout & trend_ok).fillna(False)
    exit_meanrev = close < sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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

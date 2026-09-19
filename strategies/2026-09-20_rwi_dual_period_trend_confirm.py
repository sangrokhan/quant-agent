"""Strategy: Random Walk Index (RWI, James Sibbet) dual-period trend confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-075):
Per a Google AI-overview synthesis (RTMath/GoCharting/ForexBee/strike.money;
browser_exec fallback -- web_search DDGS backend returns non-English/mangled
results this iteration) of the Random Walk Index (James Sibbet), RWI
measures how far price has traveled relative to what a random walk (pure
noise, scaled by ATR) would produce over the same period -- values above 1.0
indicate a statistically significant trend is in progress, values near/below
0 indicate range-bound/directionless conditions. The disclosed dual-period
trading rule: long entry when the LONG-term RWI High exceeds 1.0 (confirms a
significant uptrend is underway) AND the SHORT-term RWI Low also rises above
1.0 (confirms downside momentum has exhausted, i.e. a confirmed pullback-end
rather than chasing an extended move); exit when the long-term RWI High
falls back below 1.0. First Random Walk Index strategy in this repo (0 prior
hits in strategies_index.jsonl) -- structurally distinct from every existing
ATR-based indicator here (ATR trailing stops, Chandelier exits, Keltner
bands) since RWI normalizes DISPLACEMENT over a lookback by ATR*sqrt(n)
(a statistical random-walk-hypothesis test) rather than using ATR as a
volatility-scaled stop distance or band width.

RWI formula (classic Sibbet construction):
    RWI High(n) = (High_t - Low_{t-n}) / (ATR(n)_t * sqrt(n))
    RWI Low(n)  = (High_{t-n} - Low_t) / (ATR(n)_t * sqrt(n))
where ATR(n) is the standard n-period Average True Range.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _atr(df: pd.DataFrame, n: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(n).mean()


def _rwi_high(df: pd.DataFrame, n: int) -> pd.Series:
    atr = _atr(df, n)
    denom = atr * (n ** 0.5)
    return (df["high"] - df["low"].shift(n)) / denom.replace(0, np.nan)


def _rwi_low(df: pd.DataFrame, n: int) -> pd.Series:
    atr = _atr(df, n)
    denom = atr * (n ** 0.5)
    return (df["high"].shift(n) - df["low"]) / denom.replace(0, np.nan)


def generate_signals(
    price_df: pd.DataFrame,
    long_period: int = 20,
    short_period: int = 6,
    entry_threshold: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry when long-term RWI High > entry_threshold (significant
    uptrend confirmed) AND short-term RWI Low > entry_threshold (recent
    pullback has statistically exhausted). Exit when long-term RWI High
    falls back below entry_threshold.
    """
    df = _prep(price_df)

    rwi_high_long = _rwi_high(df, long_period)
    rwi_low_short = _rwi_low(df, short_period)

    entry_ok = (rwi_high_long > entry_threshold) & (rwi_low_short > entry_threshold)
    stay_ok = rwi_high_long > entry_threshold

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_vals = entry_ok.fillna(False).values
    stay_vals = stay_ok.fillna(False).values

    for i in range(len(df)):
        if in_position:
            if not bool(stay_vals[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
                in_position = True
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

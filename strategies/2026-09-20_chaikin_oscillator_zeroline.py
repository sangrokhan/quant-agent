"""Strategy: Chaikin Oscillator (Marc Chaikin) zero-line crossover, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per quantifiedstrategies.com's "Chaikin Oscillator Trading Strategy"
article (visited this iteration via browser_exec, web_search DDGS backend
TLS-connection-errored on the query) and corroborating Google SERP
snippets (Investopedia, Real Trading, WallStreetMojo -- identical formula
across all): the Chaikin Oscillator applies MACD-style momentum to the
Accumulation/Distribution Line (ADL) rather than to price:
    Money Flow Multiplier = ((Close-Low)-(High-Close)) / (High-Low)
    Money Flow Volume = MFM * Volume
    ADL = cumulative sum of Money Flow Volume
    Chaikin Oscillator = EMA(ADL, fast) - EMA(ADL, slow)  (standard 3/10)
The disclosed basic signal (also this source's own tested baseline): go
long when the oscillator crosses above zero (net buying pressure
accelerating relative to its own longer-term trend), flat when it crosses
below zero. NOTE: the source explicitly reports this exact zero-line-cross
rule tested weak on its own quantified backtests (~2.4% CAGR over 20 years
on the S&P 500, "not widely used nor well-known, perhaps for good
reasons") -- included here for completeness/independent verification on
this repo's own data/date range/asset classes rather than taking the
source's negative finding at face value without an independent check.

First Chaikin-Oscillator-derived strategy in this repo (Chaikin Money Flow
is a related but mechanically distinct indicator already tested elsewhere
in this repo's history -- CMF is a bounded ratio over one window, not a
MACD-of-ADL momentum oscillator).

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _chaikin_oscillator(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, fast: int, slow: int) -> pd.Series:
    hl_range = (high - low).replace(0, pd.NA)
    mfm = ((close - low) - (high - close)) / hl_range
    mfv = mfm.fillna(0.0) * volume
    adl = mfv.cumsum()
    return adl.ewm(span=fast, adjust=False).mean() - adl.ewm(span=slow, adjust=False).mean()


def generate_signals(
    price_df: pd.DataFrame,
    fast: int = 3,
    slow: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: Chaikin Oscillator crosses above zero.
    Exit to flat: Chaikin Oscillator crosses below zero.
    """
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]

    co = _chaikin_oscillator(high, low, close, volume, fast=fast, slow=slow)
    above_zero = co > 0
    position = above_zero.fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

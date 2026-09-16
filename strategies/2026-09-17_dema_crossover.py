"""Strategy: DEMA (Double Exponential Moving Average, Patrick Mulloy 1994)
fast/slow crossover trend-following.

Hypothesis (this cron trigger's iteration 7):
Per Patrick Mulloy's DEMA (confirmed via Google SERP synthesis this
iteration -- TMGM Trading Academy's own disclosed parameter convention:
"The standard crossover pair is 20 and 50 periods"; corroborated by
StockCharts ChartSchool ("watch for a shorter-term DEMA to cross a
longer-term DEMA") and LuxAlgo's explicit crossover definition ("fast DEMA
above slow DEMA on the current completed bar and at or below it on the
previous")): DEMA = 2*EMA(close, n) - EMA(EMA(close, n), n), designed to
reduce the lag inherent in a standard EMA by subtracting the EMA-of-EMA
overshoot. Long entry when fast DEMA (period 20) crosses above slow DEMA
(period 50, source's own disclosed standard pair); exit on the reverse
crossover. First DEMA-crossover entry in this repo (0 prior matches --
distinct from the many other adaptive/zero-lag MA families already tested,
e.g. KAMA, FRAMA, T3, VIDYA, McGinley Dynamic, none of which use DEMA's
specific "2*EMA - EMA(EMA)" overshoot-correction construction).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _dema(close: pd.Series, span: int) -> pd.Series:
    ema1 = close.ewm(span=span, adjust=False).mean()
    ema2 = ema1.ewm(span=span, adjust=False).mean()
    return 2 * ema1 - ema2


def generate_signals(
    price_df: pd.DataFrame,
    fast_period: int = 20,
    slow_period: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series: long while fast DEMA is
    above slow DEMA, flat otherwise."""
    df = _prep(price_df)
    close = df["close"]

    fast_dema = _dema(close, fast_period)
    slow_dema = _dema(close, slow_period)

    position = (fast_dema > slow_dema).astype(int)
    position = position.where(fast_dema.notna() & slow_dema.notna(), other=0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

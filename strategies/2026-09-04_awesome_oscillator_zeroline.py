"""Strategy: Awesome Oscillator (Bill Williams) zero-line crossover, trend-confirmed.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-041):
Per QuantifiedStrategies.com's Bill Williams Awesome Oscillator article
(Google AI-overview snippets first, web_search failed 5x with a DDGS/Yahoo
TLS connection error, fell back to browser_exec): the Awesome Oscillator
(AO) = 5-period SMA(median price) - 34-period SMA(median price), where
median price = (high+low)/2 (deliberately NOT close price, per Williams'
own stated rationale that median price captures intrabar volatility a
close-only calculation would miss). A bullish zero-line crossover (AO going
from below to above zero) signals a shift toward bullish short-term
momentum relative to the longer-term baseline; the source explicitly
recommends confirming an existing uptrend before trusting the crossover, so
this implementation adds a SMA(200) trend filter as that confirmation.
Long-only, per repo convention.

Signal logic
------------
- median_price = (high + low) / 2.
- AO = SMA(median_price, ao_fast) - SMA(median_price, ao_slow).
- Entry (long): AO crosses from <= 0 to > 0 (fresh cross) AND
  close > SMA(trend_window) (uptrend confirmation).
- Exit: AO crosses from > 0 to <= 0.
- Flat otherwise; long-only, no shorting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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
    ao_fast: int = 5,
    ao_slow: int = 34,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    median_price = (df["high"] + df["low"]) / 2.0

    ao = median_price.rolling(ao_fast).mean() - median_price.rolling(ao_slow).mean()

    bullish_cross = (ao > 0) & (ao.shift(1) <= 0)
    bearish_cross = (ao < 0) & (ao.shift(1) >= 0)

    sma_trend = close.rolling(trend_window).mean()
    entry = bullish_cross & (close > sma_trend).fillna(False)
    exit_signal = bearish_cross

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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

"""Strategy: Fibonacci Bollinger Bands mean reversion (inner 1.618 band touch).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-179):
Fibonacci Bollinger Bands replace the standard Bollinger Bands' fixed
standard-deviation multiplier (typically 2.0) with Fibonacci-ratio multiples
(1.618, 2.618, 4.236) of the rolling standard deviation around a central
moving average. Per TrendSpider's own documentation (the clearest free
mechanical description found this iteration -- LuxAlgo's dedicated page
404'd): "Price interactions with the bands can signal potential buy or sell
opportunities, similar to traditional Bollinger Bands." This strategy tests
the mean-reversion use case at the INNERMOST band (1.618x std, the band a
price is statistically most likely to actually reach and revert from,
analogous to this repo's existing 2-std standard-BB mean-reversion
strategy but with the Fibonacci-scaled multiplier instead): long entry when
close crosses below the lower 1.618-band, exit at the central moving average
(basis) or a max_hold_days time-stop.

Distinct from all standard-deviation-multiplier Bollinger Band strategies
already tested in this repo (dozens, e.g. 2026-09-03_bb_meanrev_qqq_volregime.py)
since the Fibonacci-ratio scaling (1.618 vs the conventional 1.5/2.0/2.5)
changes the band's statistical coverage and, per TrendSpider, is "believed to
reflect more accurately market volatility and price dynamics" -- this repo
tests that specific empirical claim rather than assuming it.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series {0,1} long/flat
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
    window: int = 20,
    fib_multiplier: float = 1.618,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    basis = close.rolling(window).mean()
    std = close.rolling(window).std()
    lower_band = basis - fib_multiplier * std

    entry = close < lower_band
    exit_meanrev = close >= basis

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

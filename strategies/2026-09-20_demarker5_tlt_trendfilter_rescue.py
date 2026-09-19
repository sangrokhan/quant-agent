"""Strategy: DeMarker(5) deep-oversold mean reversion on TLT, gated by a
long-term uptrend filter -- rescue of 2026-09-20-067 near-miss.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Direct follow-up to this cron trigger's own recorded near-miss
(2026-09-20-067, DeMarker(5) oversold on TLT, no trend filter, source's
own literal disclosed rule): best config reached Sharpe 0.988 on TLT,
just short of the 1.0 threshold across a full neighborhood scan. That
entry's own notes suggested "adding a light trend filter (the source's
own construction has none)" as a next step, following this repo's
established pattern of rescuing near-misses by adding a trend regime gate
to an otherwise-untrended oscillator signal (e.g. DeMarker on QQQ itself,
2026-09-04-154, uses exactly this fix vs. a hypothetical untrended
baseline). Same DeMarker(5)<threshold entry and next-bar-high exit as the
parent, but now additionally requires close > SMA(trend_window) (long-term
uptrend in TLT itself) before entering.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _demarker(df: pd.DataFrame, dem_window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    de_max = (high - high.shift(1)).clip(lower=0.0)
    de_min = (low.shift(1) - low).clip(lower=0.0)
    sma_max = de_max.rolling(dem_window).mean()
    sma_min = de_min.rolling(dem_window).mean()
    denom = sma_max + sma_min
    dem = (sma_max / denom).where(denom > 0, 0.5)
    return dem


def generate_signals(
    price_df: pd.DataFrame,
    dem_window: int = 4,
    oversold_threshold: float = 0.10,
    trend_window: int = 100,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: DeMarker(dem_window) < oversold_threshold AND close > SMA(trend_window).
    Exit: close > prior day's high (source's own signature exit,
    unchanged from the parent).
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    dem = _demarker(df, dem_window)
    sma = close.rolling(trend_window).mean()
    trend_filter = close > sma

    entry_trigger = ((dem < oversold_threshold) & trend_filter).shift(1).fillna(False)
    exit_trigger = (close > high.shift(1)).shift(1).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_trigger.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
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
    strategy_ret = position * daily_ret
    return strategy_ret

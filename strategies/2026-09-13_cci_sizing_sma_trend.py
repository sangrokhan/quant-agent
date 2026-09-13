"""Strategy: SMA200 trend-following gate with continuous CCI (Commodity
Channel Index) sizing overlay.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per Google SERP synthesis (Investopedia/Wikipedia/Fidelity, browser_exec):
CCI = (TypicalPrice - SMA(TypicalPrice, window)) / (0.015 * MeanDeviation),
where TypicalPrice = (High + Low + Close) / 3, and MeanDeviation is the
mean absolute deviation of TypicalPrice from its own SMA over the same
window. CCI is theoretically unbounded but conventionally interpreted via
the +/-100 band (roughly 70-80% of readings fall within it, per Lambert's
original design). This repo has 13+ prior CCI entries, all using it as a
binary threshold/crossover ENTRY signal (e.g. crossing above +100, below
-100). This iteration instead uses CCI as a CONTINUOUS SIZING dial on the
SMA(200) trend gate: exposure = clip(cci / cci_reference, 0, leverage_cap)
-- scale exposure up as CCI climbs above its reference level (fresh
momentum thrust, price well above its own recent typical-price average),
scale down toward zero as CCI falls back near/below zero even while the
slower SMA(200) trend gate is still nominally long. Structurally distinct
from every other sizing overlay tested elsewhere in this cron trigger.
First CCI-as-continuous-sizing strategy in this repo.

Signal logic
------------
- Base directional signal: long-candidate when close > SMA(trend_window).
- CCI over `cci_window` per the standard formula above.
- Exposure while trend_long: clip(cci / cci_reference, 0, leverage_cap).

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


def _cci(df: pd.DataFrame, window: int) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    sma_tp = typical_price.rolling(window).mean()
    mean_dev = typical_price.rolling(window).apply(
        lambda x: np.mean(np.abs(x - x.mean())), raw=True
    )
    cci = (typical_price - sma_tp) / (0.015 * mean_dev.replace(0, np.nan))
    return cci


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    cci_window: int = 20,
    cci_reference: float = 150.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    cci = _cci(df, cci_window)

    raw_exposure = (cci / cci_reference).astype(float)
    exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap).fillna(0.0)

    position = exposure.where(trend_long.fillna(False), other=0.0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret

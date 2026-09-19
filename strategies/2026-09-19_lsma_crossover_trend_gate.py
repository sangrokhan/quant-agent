"""Strategy: Least Squares Moving Average (LSMA) price-crossover, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-060):
Per Veles Finance's LSMA explainer (https://help.veles.finance/en/filters/lsma/),
the Least Squares Moving Average (LSMA) fits a linear regression line to
closing prices over a rolling window (default Length=25), producing a
smoother, less-lag-prone trend line than WMA/EMA because it approximates
the price trend with a mathematically precise best-fit line rather than a
simple weighted average. Trading rule: price crossing above LSMA signals
long, crossing below signals short. The source's own explicit caveat:
"LSMA works best on clearly trending markets. In sideways (flat)
conditions, the regression still tries to fit a best line through
horizontal prices -- this leads to false signals." We address this
directly (rather than trading the raw crossover) by adding a longer-term
SMA trend filter -- the same defensive pattern already validated
repeatedly in this repo for other crossover-prone indicators (KAMA, Hull
MA, T3): only take the LSMA crossover's long side when the primary asset
is ALSO in a longer-term uptrend (close > SMA(trend_window)). First
LSMA-based strategy in this repo (zero prior entries) -- a genuinely
distinct regression-based trend-line construction from every other
adaptive/weighted MA already tested.

Signal logic
------------
- LSMA[t] = linear regression fit of close over the trailing `lsma_window`
  bars, evaluated at the most recent point (offset=0).
- trend_up = close > SMA(close, trend_window) (longer-term regime filter,
  addressing the source's own sideways-market caveat).
- Entry/hold (long): close > LSMA AND trend_up.
- Exit: either condition breaks (flat) -- this is a {0,1} long/flat
  contract (not the source's raw long/short crossover) since every other
  strategy in this repo uses {0,1} unless explicitly noted otherwise, and
  a flat state during confirmed downtrends is a more conservative,
  risk-averse construction than shorting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _lsma(close: pd.Series, window: int) -> pd.Series:
    """Least Squares Moving Average: rolling linear-regression fit,
    evaluated at the most recent point of each window (offset=0)."""
    x = np.arange(1, window + 1, dtype=float)
    x_sum = x.sum()
    x2_sum = (x ** 2).sum()
    denom = window * x2_sum - x_sum ** 2

    def _fit(y: np.ndarray) -> float:
        y_sum = y.sum()
        xy_sum = (x * y).sum()
        slope = (window * xy_sum - x_sum * y_sum) / denom
        intercept = (y_sum - slope * x_sum) / window
        return slope * window + intercept  # evaluate at x = window (offset=0)

    return close.rolling(window).apply(_fit, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    lsma_window: int = 45,
    trend_window: int = 100,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    lsma = _lsma(close, lsma_window)
    sma = close.rolling(trend_window).mean()

    price_above_lsma = (close > lsma).fillna(False)
    trend_up = (close > sma).fillna(False)

    position = (price_above_lsma & trend_up).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    lsma_window: int = 45,
    trend_window: int = 100,
) -> pd.Series:
    """Return the strategy's daily return series."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(df, lsma_window=lsma_window, trend_window=trend_window)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

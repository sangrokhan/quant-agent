"""Strategy: Nearness-to-52-week-high regime filter with hysteresis, gated by
a long-term trend filter (SMA).

Hypothesis (grounded in Step 2 research this iteration):
Per https://www.quantifiedstrategies.com/52-week-high-strategy/ (visited this
iteration), academic literature (George & Hwang 2004, cited via Bayes
Business School PDF found on the same Google SERP) finds the "52-week high
effect": stocks/indices trading close to their 52-week high tend to keep
outperforming (investor anchoring bias -> under-reaction near the high),
while stocks far from their 52-week high underperform. The source's own
backtest table (buy new 52-week highs, various exits) shows a decisive edge
only when exposure is held for a while (5/10-day exits ~flat-to-negative,
50/100-day exits +1.1%/+2.2%) — i.e. hysteresis/hold-time matters, and the
source's second backtest ("52-week high strategy no.1") explicitly gates
entries with "the S&P 500 must be above its 200-day moving average" AND
"the stock must be above its 100-day moving average", so the trend filter is
part of the source's own disclosed rule, not an add-on.

Concrete rule implemented here (index/ETF-level daily-bar adaptation, since
this repo does not do stock-universe ranking):
  - nearness = (close - rolling_max(close, lookback)) / rolling_max(close, lookback)
    (0 = at/above the 52-week high, negative the further below it)
  - Long (exposure=1) when nearness >= entry_threshold (i.e. within
    entry_threshold of the 52-week high) AND close > SMA(trend_ma_window)
    (source's own 200-day-MA regime gate).
  - Stay long via a hysteresis band: only flip flat when nearness drops to/
    below exit_threshold (a wider negative threshold than entry_threshold)
    OR the trend filter breaks (close < SMA(trend_ma_window)) -- this
    directly encodes the source's finding that short holds destroy the edge
    and only a "let it run" exit rule captures it.

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


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 252,
    entry_threshold: float = -0.03,
    exit_threshold: float = -0.15,
    trend_ma_window: int = 200,
) -> pd.Series:
    """Return a 0/1 position series.

    Long while price stays within `entry_threshold` of its rolling
    `lookback`-day high and above its `trend_ma_window`-day SMA; held via
    hysteresis until nearness falls to `exit_threshold` or the trend filter
    breaks.
    """
    df = _prep(price_df)
    close = df["close"]

    rolling_high = close.rolling(lookback, min_periods=lookback // 2).max()
    nearness = (close - rolling_high) / rolling_high.replace(0.0, np.nan)
    trend_sma = close.rolling(trend_ma_window, min_periods=trend_ma_window // 2).mean()
    above_trend = close > trend_sma

    nearness_arr = nearness.fillna(-1.0).to_numpy()
    trend_arr = above_trend.fillna(False).to_numpy()

    position = np.zeros(len(close), dtype=float)
    held = 0.0
    for i in range(len(close)):
        if held == 0.0:
            if nearness_arr[i] >= entry_threshold and trend_arr[i]:
                held = 1.0
        else:
            if nearness_arr[i] <= exit_threshold or not trend_arr[i]:
                held = 0.0
        position[i] = held

    return pd.Series(position, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    lookback: int = 252,
    entry_threshold: float = -0.03,
    exit_threshold: float = -0.15,
    trend_ma_window: int = 200,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        lookback=lookback,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        trend_ma_window=trend_ma_window,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret

"""Strategy: Apirine HHLLS crossover with SMA trend filter (direct fix
for near-miss 2026-09-12-194).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-195):
Direct fix attempt for the near-miss HHLLS two-stage crossover
(2026-09-12-194, QQQ lookback_window=10 passed 4/5 validators but
narrowly failed max-drawdown at 0.257 vs the 0.25 threshold -- a 0.7pp
overshoot). That report's own diagnosis: the raw HHS/LLS crossover has no
independent long-term-trend confirmation, so it can stay long through a
broad market downtrend as long as HHS/LLS's own short-lookback dynamics
stay favorable, risking exactly the kind of drawdown blow-through observed.

This iteration adds a simple, independent trend filter (source's own
indicator has no such filter, but this repo's convention for near-miss
"add a trend/regime filter" fixes -- e.g. 2026-09-04-125's HTF-EMA fix for
the Elder Impulse System, 2026-09-11-101's ATR-trailing-stop fix for
Heikin-Ashi -- has repeatedly proven useful): require close above its own
trailing `trend_sma_window`-day SMA as an ADDITIONAL condition for holding
a long position, on top of the original HHLLS two-stage bullish
confirmation. This should cut drawdown during broad downtrends where HHS/
LLS's short lookback might otherwise stay artificially bullish.

Signal logic
------------
- Same HHS/LLS construction as 2026-09-12-194 (20-day-EMA-of-fresh-extreme-
  ratio, using `lookback_window`).
- Long entry: HHS > LLS AND HHS > 50 AND LLS < 50 (unchanged) AND
  close > SMA(trend_sma_window) (NEW).
- Exit (flatten): LLS > HHS OR (LLS > 50 AND HHS < 50) OR close falls
  below SMA(trend_sma_window) (NEW -- the trend filter is also an exit
  condition, not just an entry gate, so a trend breakdown immediately
  flattens the position).

Interface contract for validators (see validation/validators.py) and
grid_test (see validation/grid_test.py):
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).

Tunable params (all keyword args, per RESEARCH_LOOP.md Step 5 contract):
    lookback_window   (HHS/LLS lookback+EMA period, default 10, the
        near-miss's own best config).
    trend_sma_window  (NEW trend filter SMA period, default 100).
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


def _hhlls(df: pd.DataFrame, lookback_window: int):
    high = df["high"]
    low = df["low"]

    prev_high = high.shift(1)
    prev_low = low.shift(1)

    lowest_high = high.rolling(lookback_window, min_periods=lookback_window).min()
    highest_high = high.rolling(lookback_window, min_periods=lookback_window).max()
    highest_low = low.rolling(lookback_window, min_periods=lookback_window).max()
    lowest_low = low.rolling(lookback_window, min_periods=lookback_window).min()

    hh_range = (highest_high - lowest_high).replace(0.0, np.nan)
    hs_raw = (high - lowest_high) / hh_range
    hs = hs_raw.where(high > prev_high, 0.0)

    ll_range = (highest_low - lowest_low).replace(0.0, np.nan)
    ls_raw = (highest_low - low) / ll_range
    ls = ls_raw.where(low < prev_low, 0.0)

    hs = hs.fillna(0.0)
    ls = ls.fillna(0.0)

    hhs = hs.ewm(span=lookback_window, adjust=False).mean() * 100.0
    lls = ls.ewm(span=lookback_window, adjust=False).mean() * 100.0

    return hhs, lls


def generate_signals(
    price_df: pd.DataFrame,
    lookback_window: int = 10,
    trend_sma_window: int = 100,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    hhs, lls = _hhlls(df, lookback_window)
    sma = close.rolling(trend_sma_window, min_periods=trend_sma_window).mean()
    trend_up = close > sma

    bullish = (hhs > lls) & (hhs > 50) & (lls < 50) & trend_up
    bearish = (lls > hhs) | ((lls > 50) & (hhs < 50)) | (~trend_up)

    position = pd.Series(0, index=close.index, dtype=int)
    pos = 0
    warmup = max(lookback_window, trend_sma_window)
    for i in range(len(close)):
        if i < warmup:
            position.iloc[i] = 0
            continue
        if bullish.iloc[i]:
            pos = 1
        elif bearish.iloc[i]:
            pos = 0
        position.iloc[i] = pos

    return position


def generate_returns(
    price_df: pd.DataFrame,
    lookback_window: int = 10,
    trend_sma_window: int = 100,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df, lookback_window=lookback_window, trend_sma_window=trend_sma_window
    )
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

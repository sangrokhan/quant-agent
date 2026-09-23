"""Strategy: Trend Intensity Index (TII) 80/20 threshold crossover trend
following (long only).

Hypothesis (knowledge_base id TBD, this cron trigger):
Per a Google AI-overview synthesis of TII sources (TradingView/LuxAlgo/
Stonehill Forex/Trading Technologies corroborating, this iteration's
initial web_search returning empty/no-results): the Trend Intensity Index
measures how one-sided price has been relative to its own long-period SMA
-- TII = 100 * (sum of positive close-vs-SMA deviations over a trailing
deviation window) / (sum of |positive| + |negative| deviations over that
same window), bounded [0,100] with 50 as the trend/no-trend midline. The
disclosed trading rule: TII crossing above 80 signals a strong,
one-sided uptrend worth entering; TII dropping below 20 signals the trend
has reversed/exhausted (exit); the 40-60 band is an explicit chop zone to
avoid trading in. First Trend Intensity Index entry in this repo (0 prior
KB hits) -- distinct from every existing SMA-distance or %-band indicator
here because TII's ratio construction specifically measures the ASYMMETRY
of positive vs negative deviations from the SMA (how one-sided the
recent price action has been), not the raw distance or a fixed-width band.

Signal logic (long side only)
------------------------------
- SMA: rolling mean of close over `sma_period` (default 60).
- Deviation: dev_t = close_t - SMA_t.
- Positive/negative deviation sums over a trailing `dev_window` (default
  30): pos_sum = sum(max(dev,0)) over the window; neg_sum =
  sum(max(-dev,0)) over the window.
- TII_t = 100 * pos_sum / (pos_sum + neg_sum) (NaN-safe: 50 if both are 0).
- Entry: TII crosses above `entry_threshold` (default 80).
- Exit: TII drops below `exit_threshold` (default 20), or `max_hold_days`
  time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def _tii(close: pd.Series, sma_period: int, dev_window: int) -> pd.Series:
    sma = close.rolling(sma_period).mean()
    dev = close - sma
    pos_dev = dev.clip(lower=0)
    neg_dev = (-dev).clip(lower=0)
    pos_sum = pos_dev.rolling(dev_window).sum()
    neg_sum = neg_dev.rolling(dev_window).sum()
    denom = pos_sum + neg_sum
    tii = 100 * pos_sum / denom.replace(0, float("nan"))
    return tii.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    sma_period: int = 60,
    dev_window: int = 30,
    entry_threshold: float = 80.0,
    exit_threshold: float = 20.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    tii = _tii(close, sma_period, dev_window)

    above_entry = (tii > entry_threshold).fillna(False)
    cross_entry = above_entry & (~above_entry.shift(1).fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            exit_cond = (tii.iloc[i] < exit_threshold) or (held >= max_hold_days)
            if exit_cond:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if bool(cross_entry.iloc[i]):
            in_position = True
            entry_idx = i
            position.iloc[i] = 1
            continue

        position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, leverage_cap: float = 1.0, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret * leverage_cap
    return strategy_ret

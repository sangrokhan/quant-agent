"""Strategy: Time-series single-asset adaptation of Dean Markwick's "Cross
Asset Skew" replication (https://dm13450.github.io/2024/02/08/Cross-Asset-Skew-A-Trading-Strategy.html,
knowledge_base id=2026-09-09-112), itself a replication of Baltas's
cross-asset skew paper.

Source's own construction (cross-sectional, futures/ETFs across asset
classes): compute each asset's rolling skewness of daily returns over a
lookback window N (skew = mean((r-mu)/sigma)^3 over N days); go LONG assets
with NEGATIVE skew and SHORT assets with POSITIVE skew, rebalanced
periodically. Source's own stated rationale: negative skew = a cluster of
sharp down-days that is statistically likely to have overshot (mean-reversion
explanation) -> buy; positive skew = an overblown up-move likely to revert ->
sell.

This is distinct from the previously-tested skew entries in this repo
(2026-09-05-029 CBOE SKEW index vol-regime flat/long gate; 2026-09-08-055/154
skewness-regime GATE for a separate trend-following signal) -- those all use
skew as a REGIME FILTER for a different signal. This strategy instead trades
skew's OWN predictive direction directly and unconditionally: skew itself IS
the entry/exit signal (long when skew has been sufficiently negative, exit
when it recovers toward/above zero), per the source paper's literal
mean-reversion mechanism, adapted single-asset (own trailing skew vs its own
threshold, not cross-sectional ranking vs peers).

Signal logic
------------
- skew_window-day rolling skewness of daily log returns:
    skew_t = mean( ((r_i - mu)/sigma)^3 for i in [t-skew_window+1, t] )
  where mu, sigma are the rolling mean/stdev of daily log returns over the
  same window (source's exact formula, see blog post code snippet).
- Entry (long): skew_t <= entry_skew_threshold (sufficiently negative --
  source's own buy signal).
- Exit: skew_t >= exit_skew_threshold (skew has normalized/turned positive --
  mean-reversion thesis has played out), or a max_hold_days time-stop.
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rolling_skew(daily_log_ret: pd.Series, skew_window: int) -> pd.Series:
    mu = daily_log_ret.rolling(skew_window).mean()
    sigma = daily_log_ret.rolling(skew_window).std()
    standardized = (daily_log_ret - mu) / sigma
    cubed = standardized ** 3
    skew = cubed.rolling(skew_window).mean()
    return skew


def generate_signals(
    price_df: pd.DataFrame,
    skew_window: int = 60,
    entry_skew_threshold: float = -0.5,
    exit_skew_threshold: float = 0.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    daily_log_ret = (close / close.shift(1)).apply(
        lambda r: math.log(r) if r and r > 0 else None
    ).astype(float)

    skew = _rolling_skew(daily_log_ret, skew_window)

    entry = skew <= entry_skew_threshold
    exit_signal = skew >= exit_skew_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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

"""Strategy: Connors' 3-Day High/Low Method + realized-volatility regime
gate (rescue attempt for near-miss id 2026-09-20-001).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-002):
Direct rescue of this same cron trigger's prior rejection
2026-09-20-001 (Connors' 3-Day High/Low Method, both QQQ Sharpe=0.963
and SPY Sharpe=0.955 narrowly missed the 1.0 threshold, all other
validators passed cleanly). The Step 6 grid for the un-gated version
showed the edge is NOT evenly distributed across volatility regimes:
by_vol_regime pass_fraction was low=0.406, mid=0.063, high=0.313 -- the
strategy performs decisively worse in the MID-vol tercile than in either
the low- or high-vol terciles. This sub-iteration adds an explicit
realized-volatility regime gate that EXCLUDES the mid-vol regime
(restricting entries to when 20-day realized vol is either below
`vol_low_pct` or above `vol_high_pct` of its trailing 1-year distribution),
using the identical entry/exit mechanics from 2026-09-20-001 (unchanged
strategy file logic otherwise). This is the source's own trend/pullback
rule; the gate is this repo's own grid-informed addition (same rescue
pattern already used successfully elsewhere in this repo, e.g.
2026-09-18-091's 123-pattern low-vol gate and 2026-09-06-183's KAMA/ATR
low-vol gate), applied here as a two-sided exclusion rather than a
one-sided ceiling since the grid showed BOTH tails outperforming the
middle.

Interface contract for validators (see validation/validators.py) and
grid_test.py: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments.
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


def _historical_vol(close: pd.Series, window: int) -> pd.Series:
    """Annualized realized volatility (std of daily log returns * sqrt(252))."""
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(window).std() * (252 ** 0.5)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 150,
    pullback_sma_window: int = 5,
    confirm_days: int = 2,
    max_hold_days: int = 15,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_low_pct: float = 0.35,
    vol_high_pct: float = 0.65,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: identical Connors 3-Day High/Low trigger as the ungated version,
    ADDITIONALLY gated to only fire when 20d realized vol's trailing
    percentile rank (within the trailing `vol_lookback` window) is below
    `vol_low_pct` OR above `vol_high_pct` (excludes the mid-vol regime
    where the ungated grid showed the weakest edge).
    Exit: close crosses back above SMA(pullback_sma_window), or a
    max_hold_days time-stop backstop.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma_trend = close.rolling(trend_window).mean()
    sma_pullback = close.rolling(pullback_sma_window).mean()

    lower_high = high < high.shift(1)
    lower_low = low < low.shift(1)
    lower_both = (lower_high & lower_low).fillna(False)
    streak_ok = lower_both.rolling(confirm_days).sum() >= confirm_days

    uptrend = (close > sma_trend).fillna(False)
    pullback = (close < sma_pullback).fillna(False)

    vol = _historical_vol(close, vol_window)
    vol_pct_rank = vol.rolling(vol_lookback, min_periods=vol_window).apply(
        lambda x: (x < x[-1]).sum() / len(x), raw=True
    )
    vol_regime_ok = ((vol_pct_rank <= vol_low_pct) | (vol_pct_rank >= vol_high_pct)).fillna(False)

    entry_trigger = (uptrend & pullback & streak_ok & vol_regime_ok).fillna(False)
    exit_trigger = (close > sma_pullback).fillna(False)

    in_position = False
    hold_days = 0
    pos_vals = [0] * len(close)
    entry_vals = entry_trigger.values
    exit_vals = exit_trigger.values
    for i in range(len(pos_vals)):
        if in_position:
            hold_days += 1
            if exit_vals[i] or hold_days >= max_hold_days:
                in_position = False
                pos_vals[i] = 0
                hold_days = 0
            else:
                pos_vals[i] = 1
        else:
            if entry_vals[i]:
                in_position = True
                hold_days = 1
                pos_vals[i] = 1
            else:
                pos_vals[i] = 0
    position = pd.Series(pos_vals, index=close.index, dtype=int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

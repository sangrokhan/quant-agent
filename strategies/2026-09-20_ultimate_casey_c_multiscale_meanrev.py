"""Strategy: Ultimate Casey C% multi-timescale mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl):
Ali Casey's StatOasis "Ultimate C%" indicator (https://statoasis.com/overfit/research/
ultimate-c-a-smarter-mean-reversion-indicator-for-beginner-traders) and the
StrategyQuant codebase writeup (https://strategyquant.com/codebase/ultimate-casey-c/)
combine short/medium/long ROC-based percentile ranks (CaseyC%) into a single
weighted, smoothed oscillator -- unlike this repo's prior single-lookback
CaseyC% entries (2026-09-20-133 Casey Bands, 2026-09-20-134 Cumulative
CaseyC%), which use only ONE lookback window. The claimed edge is that
integrating three lookback horizons (short weighted most, long least) into
one oscillator produces more reliable oversold/overbought reversal signals
than a single-window percentile rank.

Construction (per source):
- ROC(lookback), ROC(lookback*factor), ROC(lookback*factor^2) computed.
- Each ROC series is converted to a percentile rank (CaseyC%) of its own
  trailing history (rolling window = its own lookback horizon).
- Weighted combination: short-term CaseyC% weighted most, medium next,
  long least (weights short:medium:long, normalized to sum to 1).
- Final smoothing via a rolling mean of `smooth_lookback` bars ->
  UltimateC oscillator in [0, 100].

Trading rule (source's own stated levels, generalized to entry/exit params):
- Long entry: UltimateC crosses below `entry_level` (oversold, source default 25/30).
- Exit: UltimateC crosses back above `exit_level` (source default 65/75), OR
  after `max_hold_days` bars (time-stop backstop added by this repo, not in
  the bare source article, to avoid indefinite holds through a regime where
  the oscillator never recovers).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _percentile_rank(series: pd.Series, window: int) -> pd.Series:
    """Rolling percentile rank (0-100) of the last value within its trailing window."""
    def _rank_last(x):
        if len(x) < 2:
            return np.nan
        last = x[-1]
        return 100.0 * (x < last).sum() / (len(x) - 1) if len(x) > 1 else np.nan

    return series.rolling(window, min_periods=window).apply(_rank_last, raw=True)


def _ultimate_c(
    df: pd.DataFrame,
    lookback: int = 5,
    factor: int = 3,
    smooth_lookback: int = 3,
    w_short: float = 0.6,
    w_medium: float = 0.3,
    w_long: float = 0.1,
) -> pd.Series:
    close = df["close"]

    short_w = lookback
    medium_w = lookback * factor
    long_w = lookback * factor * factor

    roc_short = close.pct_change(short_w)
    roc_medium = close.pct_change(medium_w)
    roc_long = close.pct_change(long_w)

    c_short = _percentile_rank(roc_short, short_w * 4)
    c_medium = _percentile_rank(roc_medium, medium_w * 4)
    c_long = _percentile_rank(roc_long, long_w * 4)

    total_w = w_short + w_medium + w_long
    combined = (
        w_short * c_short + w_medium * c_medium + w_long * c_long
    ) / total_w

    ultimate_c = combined.rolling(smooth_lookback, min_periods=smooth_lookback).mean()
    return ultimate_c


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 5,
    factor: int = 3,
    smooth_lookback: int = 3,
    entry_level: float = 25.0,
    exit_level: float = 75.0,
    max_hold_days: int = 10,
    w_short: float = 0.6,
    w_medium: float = 0.3,
    w_long: float = 0.1,
) -> pd.Series:
    df = _prep(price_df)
    uc = _ultimate_c(
        df,
        lookback=lookback,
        factor=factor,
        smooth_lookback=smooth_lookback,
        w_short=w_short,
        w_medium=w_medium,
        w_long=w_long,
    )

    entry_cross = (uc < entry_level) & (uc.shift(1) >= entry_level)
    exit_cross = (uc > exit_level) & (uc.shift(1) <= exit_level)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(df)):
        if not in_pos:
            if bool(entry_cross.iloc[i]):
                in_pos = True
                hold_count = 0
        else:
            hold_count += 1
            if bool(exit_cross.iloc[i]) or hold_count >= max_hold_days:
                in_pos = False
        position.iloc[i] = 1 if in_pos else 0

    return position.shift(1).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    lookback: int = 5,
    factor: int = 3,
    smooth_lookback: int = 3,
    entry_level: float = 25.0,
    exit_level: float = 75.0,
    max_hold_days: int = 10,
    w_short: float = 0.6,
    w_medium: float = 0.3,
    w_long: float = 0.1,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        lookback=lookback,
        factor=factor,
        smooth_lookback=smooth_lookback,
        entry_level=entry_level,
        exit_level=exit_level,
        max_hold_days=max_hold_days,
        w_short=w_short,
        w_medium=w_medium,
        w_long=w_long,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position * daily_returns
    return strat_returns

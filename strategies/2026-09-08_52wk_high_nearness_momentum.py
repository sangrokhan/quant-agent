"""Strategy: 52-week-high "nearness score" momentum (time-series adaptation).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-119):
Per https://quantmemo.com/strategies/fifty-two-week-high-momentum (George &
Hwang's documented 52-week-high momentum effect), a stock's price relative
to its own trailing 52-week high ("nearness score" = price / 52w_high) is a
persistent momentum signal: names trading near their 52-week high tend to
keep outperforming, because the round-number high acts as a psychological
anchor that makes investors slow to fully price in good news (anchoring
bias), producing a slow post-breakout drift rather than an efficient
instant repricing.

The source's canonical construction is CROSS-SECTIONAL (rank a stock
universe by nearness score, long the top decile). This repo's grid-test
harness evaluates single instruments (QQQ/SPY/BTC/ETH), not a cross-
sectional universe, so this is adapted to a TIME-SERIES version of the same
anchoring thesis: go long an instrument itself whenever ITS OWN nearness
score (current close / trailing 252-trading-day high) is at or above a high
threshold (i.e., trading near its own year high, "sitting right under its
yearly high" per the source's own 0.98 example), on the premise that if the
anchoring/slow-diffusion mechanism is real for cross-sectional dispersion,
it should also manifest as time-series continuation once a single
instrument is itself near its own recent high. Exit when the nearness score
drops back below an exit threshold (giving back some of the proximity) or a
max-holding-period time-stop.

Signal logic
------------
- nearness_score = close / rolling(lookback_days).max() (trailing high
  INCLUDING today, matching the source's literal "current price divided by
  the highest price over the last 52 weeks" definition).
- Entry (long): nearness_score >= entry_threshold (e.g. 0.95 = within 5% of
  the trailing high).
- Exit: nearness_score < exit_threshold (a meaningful pullback away from
  the high) OR max_hold_days elapses.
- Flat otherwise, long-only.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    lookback_days: int = 252,
    entry_threshold: float = 0.95,
    exit_threshold: float = 0.85,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trailing_high = close.rolling(lookback_days, min_periods=max(20, lookback_days // 4)).max()
    nearness = close / trailing_high

    entry = nearness >= entry_threshold
    exit_pullback = nearness < exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_pullback.iloc[i]) or held >= max_hold_days:
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

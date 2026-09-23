"""Strategy: 52-week-high nearness momentum (George & Hwang anchoring effect).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id): per
quantmemo.com's "52-Week High Momentum" strategy page
(https://quantmemo.com/strategies/fifty-two-week-high-momentum, read via
browser_exec this iteration), George & Hwang (2004) documented that stocks
trading near their 52-week high keep outperforming, because the round-number
high acts as an anchoring point that makes investors slow to fully price in
good news -- the "nearness score" (price / trailing-52-week high) predicts
future returns even controlling for plain 12-month momentum. The source's
own strategy is cross-sectional (rank a stock universe monthly, buy the top
decile), which doesn't map onto this repo's single-symbol {0,1} contract, so
this is adapted to a single-symbol time-series version: go long whenever the
nearness score itself crosses above an entry_threshold (staying near its own
high, our best available single-symbol analogue for "in the top decile"),
hold for the source's own standard "3-6 months" holding period (mapped to a
hold_days parameter, default ~126 trading days = 6 months, since the source
explicitly warns "a one-month hold... will not survive realistic costs" and
"six-month overlapping hold... is the version worth building"), exit early
if the nearness score drops back below an exit_threshold (analogous to
falling out of the top decile) or the time-stop is reached. First
52-week-high-nearness strategy in this repo (0 prior KB hits).

Signal logic
------------
- rolling_high = close.rolling(lookback_weeks*5).max() (52 weeks ~ 260
  trading days by default, but configurable).
- nearness = close / rolling_high (bounded (0, 1]).
- Entry (long): nearness crosses above entry_threshold (e.g. 0.95 -- source's
  emphasis is on names "hugging their highs").
- Exit: nearness falls below exit_threshold (e.g. 0.85, a meaningful pullback
  off the high -- analogous to dropping out of the top decile), OR
  hold_days reached (source's own 3-6 month holding-period guidance).

Interface contract matches strategies/2026-09-03_bb_meanrev_qqq_volregime.py:
generate_signals(price_df, **params) -> pd.Series {0,1}
generate_returns(price_df, **params) -> pd.Series of daily strategy returns
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
    hold_days: int = 126,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rolling_high = close.rolling(lookback_days, min_periods=lookback_days).max()
    nearness = close / rolling_high

    entry_cross = (nearness.shift(1) < entry_threshold) & (nearness >= entry_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            n = nearness.iloc[i]
            fell_below_exit = bool(n < exit_threshold) if not pd.isna(n) else False
            if fell_below_exit or held >= hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_cross.iloc[i]) if not pd.isna(entry_cross.iloc[i]) else False:
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

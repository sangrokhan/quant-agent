"""Strategy: Williams %R oversold reversal with prior-high / midline exit.

Hypothesis (source: https://quantifiedstrategies.substack.com/p/williams-r-trading-strategy-williams-203,
read 2026-09-27):
Williams %R measures where the current close sits within the recent
high-low range (0 = at the period high, -100 = at the period low). Source's
disclosed rule, backtested on SPY: enter long at the close when Williams %R
is below -90 (deep oversold, near the period's low); exit when either (a)
today's close exceeds yesterday's high (a strong reversal day - and let
profits run), or (b) Williams %R closes back above -30 (momentum has clearly
recovered). Source notes optimization across lookback period 2-25 days, with
ALL periods testing profitable (profit factor >= 1.9) and the shortest
(2-day) lookback giving the best result -- so we treat `wr_period` as a
tunable grid parameter matching that range rather than hardcoding just one
value.

First Williams %R strategy in this repo (0 prior hits for "williams_percent_r"
/ "Williams %R" in strategies_index.jsonl), distinct from every other
oscillator-threshold mean-reversion strategy here because Williams %R's
own construction (pure high-low range positioning, no smoothing/averaging)
differs from RSI (average gain/loss ratio) or Stochastic (%K with %D
smoothing) already tried extensively.

Signal logic
------------
- Williams %R (period `wr_period`) = -100 * (highest_high - close) /
  (highest_high - lowest_low), over a rolling `wr_period`-day window.
- Entry (long): Williams %R crosses from >= oversold_level down through
  < oversold_level (default -90).
- Exit: close > prior day's high (source's own "let winners run on a strong
  reversal day" rule) OR Williams %R crosses back above exit_level (default
  -30), OR a max_hold_days time-stop for safety (this repo's convention;
  source didn't disclose one, but every other mean-reversion strategy here
  uses one to avoid indefinite holds).

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _williams_r(df: pd.DataFrame, period: int) -> pd.Series:
    highest_high = df["high"].rolling(period).max()
    lowest_low = df["low"].rolling(period).min()
    denom = (highest_high - lowest_low).replace(0, pd.NA)
    wr = -100 * (highest_high - df["close"]) / denom
    return wr


def generate_signals(
    price_df: pd.DataFrame,
    wr_period: int = 2,
    oversold_level: float = -90.0,
    exit_level: float = -30.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    wr = _williams_r(df, wr_period)

    below_oversold = wr < oversold_level
    entry = below_oversold & (~below_oversold.shift(1).fillna(False))

    prior_high = high.shift(1)
    exit_strong_reversal = close > prior_high
    exit_midline = wr > exit_level

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(df)):
        if in_position:
            held = i - entry_idx
            if (
                bool(exit_strong_reversal.iloc[i])
                or bool(exit_midline.iloc[i])
                or held >= max_hold_days
            ):
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

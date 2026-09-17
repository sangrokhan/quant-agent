"""Strategy: Range-compression mean reversion with IBS confirmation
(10-day high minus 2.5x 25-day average range, IBS<0.3 entry).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-178):
Per a disclosed r/algotrading post ("Found a simple mean reversion setup
with 70% win rate but only invested 20% of the time", u/vaanam-dev,
https://www.reddit.com/r/algotrading/comments/1rjvxjy/, read this iteration
via browser_exec after web_search DDGS backend errored on the initial
query): a pullback deep enough to close below (10-day high - 2.5 x the
25-day average daily range) marks a statistically extreme short-term
decline; when that close ALSO shows weak intrabar strength (IBS < 0.3,
i.e. closed in the bottom 30% of its own day's range -- a capitulation-like
close), the setup mean-reverts with a reported ~70-75% historical win rate
on SPY/QQQ/AAPL (2006-2026 sample). Exit is simply the first close that
exceeds the prior day's high (trend resumption). This combines an
ATR-like RANGE-DEVIATION threshold (distinct from this repo's existing
ATR-percentage or Bollinger-Band deviation constructions -- here the
deviation is measured against a fixed high-water mark, not a rolling mean)
with an IBS confirmation filter (already used elsewhere in this repo, but
not in this exact combination/threshold).

Signal logic
------------
- range_avg = mean of (daily high - daily low) over the trailing
  range_window (25) days.
- high_water = highest HIGH over the trailing high_window (10) days.
- Entry (long): today's close < high_water - deviation_mult * range_avg
  (source's own default deviation_mult=2.5), AND IBS = (close-low)/(high-low)
  < ibs_threshold (source's own default 0.3). Both computed causally using
  data up to and including today's own bar (matches the source's own
  same-day IBS-at-close entry rule).
- Exit: close > yesterday's high (source's own exact exit rule), or a
  max_hold_days safety backstop (source's own longest observed trade was
  ~29 days; a generous backstop here avoids indefinite holds without
  materially altering the source's own mechanism).
- Flat otherwise; long-only, single position at a time.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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
    high_window: int = 10,
    range_window: int = 25,
    deviation_mult: float = 2.5,
    ibs_threshold: float = 0.3,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    n = len(close)

    daily_range = high - low
    range_avg = daily_range.rolling(range_window, min_periods=range_window).mean()
    high_water = high.rolling(high_window, min_periods=high_window).max()
    ibs = (close - low) / (high - low).replace(0, pd.NA)

    entry = (close < (high_water - deviation_mult * range_avg)) & (ibs < ibs_threshold)
    entry = entry.fillna(False)

    prior_high = high.shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_days = 0

    for i in range(n):
        px_close = close.iloc[i]
        ph = prior_high.iloc[i]

        if in_position:
            hold_days += 1
            if (ph == ph and px_close > ph) or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if bool(entry.iloc[i]):
            in_position = True
            hold_days = 0
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

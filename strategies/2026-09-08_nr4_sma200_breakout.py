"""Strategy: NR4 (Narrow Range 4) breakout with SMA200 trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-031):
Per the "Narrow Range 4" (NR4) pattern (a shorter-lookback variant of Toby
Crabel's NR7 concept), as described in Google's SERP synthesis of
strategydecoder.app's "NR4 Pattern Breakout with SMA 200 Filter" page and
forexfactory.com's definition ("current bar's range is the smallest range
of any of the last four bars... a sign of indecision with the current
trend"): a bar whose high-low range is the narrowest of the trailing 4
bars marks a volatility contraction; combined with a long-term SMA200
trend filter (rather than the already-tested NR7 strategy's 20-period
EMA), a breakout above the NR4 bar's high in an established SMA200
uptrend is a lower-risk trend-continuation long entry.

Distinct from the existing repo NR7 strategy (2026-09-04-081, rejected,
Sharpe 0.617 best full-sample) via: (a) a much shorter 4-bar contraction
window (more frequent, less selective signal vs the 7-bar window) and
(b) a slow SMA200 trend filter (long-horizon regime confirmation) instead
of a fast 20-period EMA (short-horizon trend confirmation) -- a
materially different selectivity/trend-confirmation tradeoff.

Signal logic
------------
- SMA(trend_window) is the trend filter (default 200, matching source).
- For each bar, look at the trailing `nr_window` bars (inclusive of the
  current bar, default 4): if the current bar's (high - low) range is the
  smallest of that window, it's an NR (narrow-range) bar.
- Trend confirmation: close is above the SMA(trend_window) on the NR bar.
- Entry (long): within a short lookahead window after a confirmed NR bar,
  close breaks above the NR bar's high while still above the SMA trend
  filter.
- Exit: close drops back below the SMA trend filter, or a max_hold_days
  time-stop, whichever comes first.
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py).
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
    nr_window: int = 4,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    bar_range = high - low
    is_narrowest = bar_range == bar_range.rolling(nr_window).min()

    sma = close.rolling(trend_window).mean()
    above_sma = close > sma

    nr_confirmed = (is_narrowest & above_sma).fillna(False)
    nr_bar_high = high.where(nr_confirmed)
    trigger_level = nr_bar_high.ffill()

    bars_since_nr = (~nr_confirmed).groupby((nr_confirmed).cumsum()).cumcount()
    breakout = (close > trigger_level) & (bars_since_nr <= 5) & above_sma & trigger_level.notna()

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            still_trend = bool(above_sma.iloc[i]) if not pd.isna(above_sma.iloc[i]) else False
            if hold_count >= max_hold_days or not still_trend:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(breakout.iloc[i]):
                in_pos = True
                hold_count = 0
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

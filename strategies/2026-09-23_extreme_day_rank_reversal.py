"""Strategy: Extreme-day-rank mean reversion (long only) -- go long after the
N lowest daily returns of the trailing lookback period.

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Per Quantpedia's "Automated Trading Edge Analysis"
(https://quantpedia.com/automated-trading-edge-analysis, read this
iteration via browser_exec), the simplest trading-edge idea they tested
with a clear positive result was: each day, check if today's daily return
belongs to the N lowest returns of the trailing lookback (their own
figures: N=25 lowest of the past 250 trading days); if so, go long the
next day. The source explicitly found this construction produced "a
positive trading edge" with "a pretty nice and stable equity curve" for
the long side (the short-side mirror, going short after the N highest
returns, only worked in bear markets and was noted as not reliably
edge-positive -- so this strategy tests LONG ONLY, per the source's own
distinction). This is a rank-based (percentile-position) extreme-day
filter, distinct from this repo's existing z-score/PercentRank(ROC)-based
mean-reversion constructions (e.g. 2026-04-121 Alvarez PercentRank(ROC),
2026-09-17-184 price z-score) because it ranks the RAW SINGLE-DAY RETURN
itself (not a multi-day ROC or a continuously-distributed z-score) against
its own trailing distribution via an explicit rank-count threshold.

Signal logic
------------
- daily_return = close.pct_change()
- rank_today = daily_return's rank (ascending) within the trailing
  lookback-day window (today's return compared to the prior lookback-1
  days plus itself).
- extreme_low = rank_today <= n_extreme (today's return is among the
  n_extreme lowest of the trailing lookback days).
- Entry (long): extreme_low triggers a long entry effective NEXT bar
  (captured naturally by the standard shift(1) exposure convention in
  generate_returns -- position set today, return realized next bar).
- Exit: after hold_days trading days (fixed holding period, matching the
  source's own simple "go long the next day" -- no explicit exit rule
  disclosed by the source beyond that, so this repo adds a fixed
  short-term hold consistent with the source's short-term-reversal
  framing).
- Optional close>SMA(trend_window) uptrend gate (trend_filter=True by
  default, standard practice elsewhere in this repo to avoid buying
  extreme drops in structural downtrends).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 250,
    n_extreme: int = 25,
    hold_days: int = 5,
    trend_window: int = 200,
    trend_filter: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    daily_return = close.pct_change()
    # Rank each day's return within its own trailing `lookback` window
    # (ascending rank: rank 1 = lowest return in the window).
    rank_in_window = daily_return.rolling(lookback).apply(
        lambda w: pd.Series(w).rank(ascending=True).iloc[-1], raw=False
    )
    extreme_low = (rank_in_window <= n_extreme).fillna(False)

    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False) if trend_filter else pd.Series(True, index=close.index)

    entry = extreme_low & uptrend

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= hold_days:
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

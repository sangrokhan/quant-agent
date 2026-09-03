"""Strategy: Day-of-the-week effect (Monday-close-to-Tuesday-close), a.k.a.
"Turnaround Tuesday".

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-018),
sourced from https://www.quantifiedstrategies.com/day-of-the-week-effect/
(Oddmund Groette, QuantifiedStrategies.com). Methodology quoted directly
from the source: "We buy at the close on weekdays 1-5. 1 is Monday and 5 is
Friday. We exit at the close the next day." Their reported finding across
five indices (S&P 500, DAX 40, OMX 30, Nifty 50, Hang Seng), tested
2000-Sept 2021: the single best trading-day slot across nearly every index
tested was "weekday 1" -- buy at Monday's close, hold, sell at Tuesday's
close -- averaging +0.12% on the S&P 500 alone. This is the empirical basis
for the well-known "Turnaround Tuesday" seasonal pattern. The source
attributes no single universally-agreed causal mechanism but notes this
slot is consistently the best (or near-best) across multiple unrelated
equity indices, suggesting a real (if small) structural day-of-week
seasonality rather than a single-market fluke.

This is a long-only, purely calendar-based signal (no price/volume
indicator at all) -- distinct from every prior calendar-anomaly strategy in
this repo: turn-of-month (2026-09-03-006, month-boundary window),
overnight-drift (2026-09-03-007, close-to-open sub-daily session split),
and gap-down-fade (2026-09-03-010, open-to-close session conditioned on a
gap trigger). This strategy instead holds one full calendar trading day
(day t's full-session return) whenever day t's weekday matches a fixed
target (default Tuesday), and is flat every other day of the week --
testing whether a specific weekday of the 5-day week alone carries a
positive-return edge, with no monthly or session-timing component at all.

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    target_weekday: int = 1,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long only on trading days whose calendar weekday equals
    `target_weekday` (Python `.weekday()` convention: Monday=0, Tuesday=1,
    Wednesday=2, Thursday=3, Friday=4). Default target_weekday=1 (Tuesday)
    reproduces the source's best-performing "weekday 1" slot (Monday close
    -> Tuesday close). Flat on every other day of the week.
    """
    df = _prep(price_df)
    idx = df.index
    weekday = pd.Series(idx.weekday, index=idx)
    position = (weekday == target_weekday).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    Position is computed from the day's own weekday (not lagged from a
    prior-day signal -- the calendar identity of "today" is known in
    advance, unlike a price-derived signal), but the position is still
    shift(1)-applied against daily_ret so that the return realized on day t
    correctly represents holding from day t-1's close (yesterday, e.g.
    Monday close) to day t's close (today, e.g. Tuesday close) -- exactly
    matching the source's "buy at close, exit at close next day" test
    methodology and avoiding any look-ahead bias for consistency with every
    other strategy in this repo.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

"""Strategy: Day-of-week-conditional overnight gap continuation (Wednesday effect).

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per SharePlanner's SPY/QQQ overnight-gap-by-weekday analysis
(https://www.shareplanner.com/blog/strategies-for-trading/fading-the-gap-how-large-overnight-moves-in-spy-and-qqq-play-out-during-the-trading-day.html),
1%+ overnight gap-ups do NOT behave uniformly across weekdays: Monday
gap-ups are disproportionately faded intraday (14% full reversal vs ~10%
baseline), while Wednesday gap-ups show the strongest continuation (67% of
1%+ Wednesday gap-ups continued rising open-to-close, with an average
additional +0.5% intraday gain). This is distinct from every prior gap
strategy in this repo (14+ entries, all using an unconditional/unfiltered
gap-fade or gap-continuation rule with no day-of-week interaction) and from
every prior day-of-week strategy (e.g. Turnaround Tuesday variants, OPEX
week) which don't use gap size at all.

Signal logic
------------
- Overnight gap_pct = (today's open - yesterday's close) / yesterday's close.
- On a chosen target weekday (default Wednesday = weekday() == 2), if
  gap_pct >= min_gap_pct, go long from that day's open to that day's close
  only (single-day trade, no overnight hold -- this directly mirrors the
  source's own open-to-close continuation statistic, not a multi-day swing).
- Flat every other day (including non-qualifying gaps on the target weekday,
  and every day that isn't the target weekday).

The grid test (Step 6) sweeps `weekday` across all five trading weekdays to
check whether Wednesday specifically is where the edge concentrates (per the
source's claim) versus other days -- this is the key falsifiable part of
the hypothesis, not just "gap continuation works somewhere".

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).
    generate_signals(price_df, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index (1 = long that day
        only, 0 = flat).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _gap_and_dow(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    open_ = df["open"]
    close = df["close"]
    prior_close = close.shift(1)
    gap_pct = (open_ - prior_close) / prior_close
    dow = pd.Series(df.index.dayofweek, index=df.index)
    return gap_pct, dow


def generate_signals(
    price_df: pd.DataFrame,
    weekday: int = 2,  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri
    min_gap_pct: float = 0.01,
) -> pd.Series:
    """Return a {0,1} position series: long only on qualifying target-weekday
    gap-up days (single-day hold, open->close)."""
    df = _prep(price_df)
    gap_pct, dow = _gap_and_dow(df)

    qualifies = (dow == weekday) & (gap_pct >= min_gap_pct)
    signal = qualifies.astype(int)
    signal = signal.reindex(df.index).fillna(0).astype(int)
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    weekday: int = 2,
    min_gap_pct: float = 0.01,
) -> pd.Series:
    """Daily strategy returns: on qualifying days, the day's own open->close
    return; 0 otherwise (single-day trade, no overnight exposure)."""
    df = _prep(price_df)
    signal = generate_signals(price_df, weekday=weekday, min_gap_pct=min_gap_pct)

    open_ = df["open"]
    close = df["close"]
    day_return = (close - open_) / open_

    strat_returns = signal * day_return
    strat_returns = strat_returns.reindex(df.index).fillna(0.0)
    strat_returns.name = "strategy_returns"
    return strat_returns

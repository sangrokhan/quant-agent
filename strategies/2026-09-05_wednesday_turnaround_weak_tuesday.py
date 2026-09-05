"""Strategy: Wednesday Turnaround (weak-Tuesday day-of-week mean reversion).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-073):
QuantifiedStrategies.com's "Wednesday Turnaround Strategy" is explicitly
described as "a cousin of the Tuesday Turnaround Strategy" (backtest
disclosed for SPY: 330 trades, 0.7% avg gain/trade, 63% win ratio, profit
factor 2.1, CAGR 6.6%, exposure 19%, MDD 21% -- exact numeric rule
paywalled on the Wednesday article itself). The companion "Turnaround
Tuesday Strategy" article discloses its own underlying mechanism in a
Google search snippet: "One approach involves buying on a weak Monday,
where the close is at least 1% lower than Friday's close, and selling at
Tuesday's close." This hypothesis operationalizes the disclosed "cousin"
relationship by shifting that exact mechanism one weekday forward: buy on a
weak Tuesday (close at least weak_pct% lower than Monday's close), sell at
Wednesday's close. Distinct from the already-rejected plain
Monday-close->Tuesday-close "Turnaround Tuesday" (2026-09-03-018, no
weakness-magnitude gate) and its volume-gated variant (2026-09-04-105) --
this is the WEAK-CLOSE-MAGNITUDE-gated Tuesday->Wednesday variant, a
distinct day-pairing AND a distinct (percentage-drop) gating mechanism
neither prior day-of-week entry used.

Signal logic
------------
- Identify each Tuesday's close vs the prior trading day's (typically
  Monday's) close.
- Entry (long) at Tuesday's close if that close is <= (1 - weak_pct) times
  the prior day's close (a "weak Tuesday").
- Exit at Wednesday's close (held for exactly one trading day; flat
  otherwise).

Interface contract (RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
    weak_pct: float = 0.01,
    entry_weekday: int = 1,  # Tuesday = 1 (Monday=0)
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long from `entry_weekday`'s close through the next trading day's close,
    but ONLY on weeks where `entry_weekday`'s close dropped by at least
    `weak_pct` vs the prior trading day's close (the "weakness" gate).
    Position is 1 on `entry_weekday` (held overnight into next day) when the
    weakness condition triggers, 0 otherwise.
    """
    df = _prep(price_df)
    idx = df.index
    close = df["close"]
    prior_close = close.shift(1)

    weekday = pd.Series(idx.weekday, index=idx)
    is_entry_day = weekday == entry_weekday
    weak_close = close <= prior_close * (1.0 - weak_pct)

    entry = is_entry_day & weak_close.fillna(False)

    position = pd.Series(0, index=idx, dtype=int)
    position[entry] = 1
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Position set on entry_weekday's close is held INTO the next trading
    # day's close (no extra lag needed: shift(1) here means "was the
    # position ON at the START of today", i.e. entered at yesterday's
    # close -- which is exactly the entry_weekday's close, capturing that
    # day's close-to-next-close return without look-ahead).
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

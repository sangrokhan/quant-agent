"""Strategy: Halloween Indicator / "Sell in May and Go Away" seasonal switch.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-104):
Per the well-documented "Halloween Indicator" (Bouman & Jacobsen 2002 and
the broader "Sell in May and Go Away" literature, corroborated across
Capital.com/ResearchGate/Emerald/Marotta-on-Money search results), equities
have historically produced almost all of their long-run gains during the
Nov 1 - Apr 30 window ("best six months"), with the May 1 - Oct 31 window
("worst six months") contributing little to no average return. This is a
fixed calendar-only rule (no technical indicator, no price-derived signal)
-- distinct from every other calendar-anomaly strategy already tested in
this repo (turn-of-month, day-of-week, pre-holiday, crypto weekend) since
it operates on a 6-month hold horizon rather than a multi-day window.

Signal logic
------------
- Long (position=1) on any trading day whose calendar month is in
  {Nov, Dec, Jan, Feb, Mar, Apr} (configurable start/end month, default
  best_start_month=11, best_end_month=4, i.e. wrapping across year-end).
- Flat (position=0) otherwise (May through Oct).
- No entry/exit lag needed beyond the existing daily-return shift
  convention used throughout this repo (position decided using info as of
  the close, applied to the next day's return).
- Testing on crypto (BTC/ETH, 24/7, no institutional fiscal-year/tax-loss
  cycle that Sell-in-May's own explanations rely on) as a falsification
  check -- if a real behavioral/fiscal-year mechanism drives this, it
  should NOT transfer cleanly to a market without that structure.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _in_best_months(month: int, best_start_month: int, best_end_month: int) -> bool:
    """True if `month` falls within the [best_start_month, best_end_month]
    range, wrapping across year-end when best_start_month > best_end_month
    (e.g. 11 -> 4 means Nov, Dec, Jan, Feb, Mar, Apr)."""
    if best_start_month <= best_end_month:
        return best_start_month <= month <= best_end_month
    return month >= best_start_month or month <= best_end_month


def generate_signals(
    price_df: pd.DataFrame,
    best_start_month: int = 11,
    best_end_month: int = 4,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    months = df.index.month
    position = pd.Series(
        [1 if _in_best_months(m, best_start_month, best_end_month) else 0 for m in months],
        index=df.index,
        dtype=int,
    )
    return position


def generate_returns(
    price_df: pd.DataFrame,
    best_start_month: int = 11,
    best_end_month: int = 4,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(df, best_start_month=best_start_month, best_end_month=best_end_month)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

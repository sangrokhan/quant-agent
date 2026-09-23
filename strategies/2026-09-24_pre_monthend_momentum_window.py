"""Strategy: Pre-month-end momentum window (D-10 to D-5), gated by the
asset's own trailing 252-day momentum sign.

Hypothesis (knowledge_base id 2026-09-24-002):
Per Quantpedia's "Sectoral Intramonth Momentum Cycle: Exploiting
Turn-of-the-Month Patterns in Sector ETF Strategies" (Aug 2026,
https://quantpedia.com/sectoral-intramonth-momentum-cycle/), sector-ETF
momentum has a distinct "Leg Three" that re-emerges specifically in the
window from 10 to 5 trading days before month-end -- citing Nathan,
Suominen & Tasa (2026)'s single-stock finding that momentum returns
concentrate in a short pre-month-end window driven by institutional
month-end "dash for cash" (selling dispensable/loser positions). The
source's own construction is a full cross-sectional 9-sector-ETF
long-top-3/short-bottom-3 (or short-SPY) portfolio, which is infeasible
with this repo's single-symbol `generate_returns(price_df, **params)`
contract (same feasibility limitation already documented for other
sector-rotation/relative-strength-ranking rejections in this repo).

This strategy instead operationalizes the SAME temporal window and
mechanism at single-asset granularity: hold the asset the D-10-to-D-5
window before each month-end ONLY IF its own trailing 252-day return is
positive (reusing the same "trailing momentum ranking, timed to a specific
pre-month-end window" logic the source uses, just applied long-only to a
single symbol's own sign rather than a cross-sectional rank), flat
otherwise and flat the rest of the month. Distinct from all prior
calendar-seasonal entries in this repo (turn_of_month, day_of_week,
opex_week, santa_claus, january_effect, pre_holiday_effect) since none use
this specific D-10-to-D-5 pre-month-end window or gate it by trailing-252d
momentum sign.

Signal logic
------------
- Compute each bar's trading-days-before-month-end (using calendar month
  boundaries of the actual trading calendar present in price_df).
- mom_252 = close.pct_change(mom_window) (default 252).
- Long only when: (days_before_month_end is between window_start=10 and
  window_end=5 inclusive) AND mom_252 (as of the most recent month-end) > 0.
- Flat at all other times (including the rest of the month).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _trading_days_before_month_end(index: pd.DatetimeIndex) -> pd.Series:
    """For each bar, count trading days remaining until (and including) the
    last trading day of that calendar month, using ONLY the trading days
    actually present in `index` (no calendar-day assumptions)."""
    months = index.to_period("M")
    df = pd.DataFrame({"month": months}, index=index)
    # rank within each month, counting from the end (0 = last trading day
    # of month, 1 = second-to-last, etc.)
    days_before_end = df.groupby("month").cumcount(ascending=False)
    return pd.Series(days_before_end.values, index=index)


def generate_signals(
    price_df: pd.DataFrame,
    mom_window: int = 252,
    window_start: int = 10,
    window_end: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    days_before_end = _trading_days_before_month_end(df.index)
    in_window = (days_before_end <= window_start) & (days_before_end >= window_end)

    # trailing momentum computed from the most recent month-end (day 0) --
    # approximate by using the momentum as of the start of the window
    # (i.e. the last available trailing-252d return, which changes daily
    # but is dominated by the same underlying trend the source's monthly
    # ranking would capture).
    mom_252 = close.pct_change(mom_window)
    mom_positive = mom_252 > 0

    position = (in_window & mom_positive.fillna(False)).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    mom_window: int = 252,
    window_start: int = 10,
    window_end: int = 5,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, mom_window=mom_window, window_start=window_start, window_end=window_end
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret

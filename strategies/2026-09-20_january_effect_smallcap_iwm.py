"""Strategy: January Effect — small-cap (IWM) seasonal long window,
mid-December through mid-January.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-022):
The "January Effect" (Rozeff & Kinney 1976, corroborated by Yale Hirsch's
Stock Trader's Almanac and QuantifiedStrategies.com's "200 Trading
Strategies" roundup) documents small-cap stocks historically outperforming
large caps in a window running from mid-December through mid-January,
commonly attributed to December tax-loss-selling pressure on small caps
reversing once the new tax year begins (small-cap sellers no longer need to
realize losses, buying demand returns) plus institutional
window-dressing/rebalancing flows. Practitioner sources (Michael Nauss
CMT / StatsEdgeTrading video summary via SERP, Hirsch's own Almanac
commentary) frame the modern practical window as beginning in
mid-December (buy) and running through mid-January (sell), applied to
small-cap proxies like IWM (Russell 2000 ETF).

This repo has an existing December-window seasonal entry (Santa Claus
Rally / turn-of-year family) and a 4-Year Presidential Election Cycle
seasonality (2026-09-08-163), but has NEVER traded IWM (small-cap) as a
distinct symbol, nor tested this specific December-to-January small-cap
seasonal window -- genuinely new symbol and genuinely new calendar
construction.

Signal logic
------------
- entry_month/entry_day (default December 15) marks the start of the long
  window each calendar year.
- exit_month/exit_day (default January 15, of the FOLLOWING calendar year)
  marks the end of the long window.
- Long (position=1) on the first trading day on/after entry_month/day each
  December, held through the first trading day on/after exit_month/day the
  following January; flat all other calendar days.
- Tested on IWM (small-cap, the source's own primary proxy) as well as
  SPY/QQQ (large-cap controls, testing whether the effect is genuinely
  small-cap-specific or just a generic December-January seasonal
  tailwind already captured by other entries) and BTC/ETH (crypto has no
  tax-year-driven small-cap analogy, included as a falsification check
  per this repo's standard practice for calendar-effect strategies).
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
    entry_month: int = 12,
    entry_day: int = 15,
    exit_month: int = 1,
    exit_day: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series for the Dec->Jan small-cap window."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    position = pd.Series(0, index=idx, dtype=int)
    in_window = False

    for i in range(n):
        ts = idx[i]
        month, day = ts.month, ts.day

        is_entry_day = (month == entry_month) and (day >= entry_day)
        is_still_dec_after_entry = (month == entry_month and day >= entry_day) or (
            month > entry_month if entry_month < 12 else False
        )
        is_exit_reached = (month == exit_month) and (day >= exit_day)

        if not in_window:
            if is_entry_day:
                in_window = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
        else:
            # We're in the window; check whether we've crossed the exit
            # threshold (which occurs in the FOLLOWING January).
            if month == exit_month and day >= exit_day:
                in_window = False
                position.iloc[i] = 0
            elif month == exit_month or (exit_month == 1 and month == entry_month):
                # Within January before exit_day, or still in December
                # after entry -- stay long.
                position.iloc[i] = 1
            elif entry_month <= month <= 12 and month != exit_month:
                # Still December (or later months if entry_month < 12),
                # before wrapping into the exit month.
                position.iloc[i] = 1
            else:
                # Any other month means we've overshot without hitting the
                # exit condition (e.g. gap in trading days) -- exit
                # defensively rather than holding indefinitely.
                in_window = False
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

"""Strategy: Small-gap-down intraday gap-fill mean reversion (daily-bar
OHLC approximation, no intraday data required).

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-26-032):
Per tradethatswing.com's "S&P 500 (SPY) Gap Fill Strategy and Statistics"
(Cory Mitchell, CMT, read via browser_exec -- web_search's DDGS backend
worked for this query, but the article itself was read via browser_exec
render since the source uses a paid "Edgeful" real-time-stats table that
web_extract would not reliably render): small gaps fill much more often
than large ones -- source's own disclosed statistics (6-month sample,
SPY, uptrend regime): gap-down 0-0.19% fills 92% of the time, gap-down
0.2%-0.39% fills 69% of the time, day-of-week varying 20%-80%. Source's
own trade construction: buy at the open after a gap-down, exit at the
prior day's close once price touches it intraday (its "100% gap fill"
level), or hold the full day if it never touches (source recommends
combining with an opening-range-breakout entry filter and a 15-minute
stop, but that requires intraday/minute bars which this repo's
data/loaders.py does not provide -- daily OHLC only).

This repo's daily-bar OHLC IS sufficient to approximate the core
gap-fill mechanic without needing intraday bars, because "did the price
touch the prior close during the day" is directly observable from the
day's own Low (for a gap-down) or High (for a gap-up) versus the prior
close level -- no sub-daily resolution needed for that yes/no fact, only
for the exact intraday exit TIMING (which we approximate as "exit at the
gap-fill level if touched, else exit at the day's own close", a
same-day round-trip, never held overnight).

Signal / return logic
----------------------
- gap_pct = (open_t - close_{t-1}) / close_{t-1}
- Only trade gap-DOWNS of moderate size: -max_gap_pct <= gap_pct <=
  -min_gap_pct (source's own finding: very small gaps fill most
  reliably; the day-of-week filter is source's own disclosed table,
  applied here as an optional weekday allow-list).
- Entry: buy at that day's OPEN.
- Exit (same day, no overnight hold): if low_t <= close_{t-1} (gap
  filled intraday), exit at close_{t-1} (the fill level) --> daily
  return = (close_{t-1}/open_t) - 1, which is POSITIVE for a gap-down
  entry since close_{t-1} > open_t. If the gap never fills that day,
  exit at close_t instead --> daily return = (close_t/open_t) - 1.
- No position held overnight (each trade is confined to a single day's
  bar), consistent with source's own same-day gap-fill framing.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1, 1 on days
    the strategy takes the trade -- since exit always happens same day,
    this is really an "active that day" indicator, not a held position).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


_WEEKDAY_NAME_TO_INT = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4,
}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _eligible_days(
    df: pd.DataFrame, min_gap_pct: float, max_gap_pct: float, allowed_weekdays
) -> pd.Series:
    prior_close = df["close"].shift(1)
    gap_pct = (df["open"] - prior_close) / prior_close
    is_gap_down = (gap_pct <= -min_gap_pct) & (gap_pct >= -max_gap_pct)
    if allowed_weekdays is not None:
        weekday_ok = pd.Series(df.index.dayofweek, index=df.index).isin(allowed_weekdays)
    else:
        weekday_ok = pd.Series(True, index=df.index)
    eligible = is_gap_down.fillna(False) & weekday_ok
    return eligible


def generate_signals(
    price_df: pd.DataFrame,
    min_gap_pct: float = 0.001,
    max_gap_pct: float = 0.004,
    allowed_weekdays=None,
) -> pd.Series:
    """Return a {0,1} indicator of days this strategy takes a same-day
    gap-fill trade (1 = active that day, 0 = flat). `allowed_weekdays`
    is an optional iterable of ints (0=Mon..4=Fri) restricting entries to
    specific days per source's own day-of-week fill-rate table."""
    df = _prep(price_df)
    eligible = _eligible_days(df, min_gap_pct, max_gap_pct, allowed_weekdays)
    return eligible.astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    min_gap_pct: float = 0.001,
    max_gap_pct: float = 0.004,
    allowed_weekdays=None,
) -> pd.Series:
    """Daily strategy returns: on eligible gap-down days, buy at open and
    exit at the prior close if the gap fills intraday (low <= prior
    close), else exit at that day's own close. Zero on all other days.
    Same-day round-trip only -- never held overnight."""
    df = _prep(price_df)
    eligible = _eligible_days(df, min_gap_pct, max_gap_pct, allowed_weekdays)

    prior_close = df["close"].shift(1)
    open_ = df["open"]
    low = df["low"]
    close = df["close"]

    gap_filled = low <= prior_close
    exit_price = np.where(gap_filled, prior_close, close)
    day_return = (exit_price / open_) - 1.0

    strat_ret = pd.Series(np.where(eligible, day_return, 0.0), index=df.index)
    return strat_ret.fillna(0.0)

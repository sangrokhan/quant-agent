"""Strategy: Classic Monday/Friday day-of-week seasonality (long-only adaptation).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-096):
Per https://tradesaveplus.com/blog/day-of-week-effect-in-trading, the
original 1980s academic "weekend effect" / "Monday effect" found US equity
returns on Mondays were, on average, negative, while Friday returns were
"unusually positive" -- historically traded as "short into the close on
Friday, cover on Monday morning." This repo's SAFETY.md/long-only
convention precludes the short leg, so the long-only mirror is tested here:
be long only from Thursday's close through Friday's close (capturing the
historically positive Friday session), and flat over the weekend gap and
through Monday (avoiding the historically negative Monday exposure).

The source itself is explicitly SKEPTICAL of this effect holding up today
("the effect shrank as more people knew about it... a lot of the original
result was concentrated in small-cap stocks, specific decades") -- this is
tested here as a falsification check on this repo's own QQQ/SPY/BTC/ETH
sample (2019-2026, decades after the original discovery), not because the
source itself endorses it as still live. First calendar/day-of-week
seasonality strategy in this repo (distinct from prior monthly seasonality
patterns already tested: Turn-of-Month, January Effect, Santa Claus Rally,
FOMC-day effects).

Signal logic
------------
- Long only on Fridays (position=1 on the bar whose weekday is Friday,
  i.e. held from Thursday's close through Friday's close via the
  standard next-day-return convention already used by every strategy in
  this repo).
- Flat every other weekday (Monday-Thursday) and on any day crypto trades
  that isn't Friday (crypto trades 7 days/week -- weekday index still
  applies to identify "Friday" bars in the daily-bar timestamp index).
- No parameters to tune other than which weekday to go long (trivially a
  discrete choice, not a continuous grid) -- included as a param for the
  grid test's sake (long_weekday, default 4=Friday) to let the grid also
  sanity-check other weekdays as a specificity check.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    long_weekday: int = 4,  # 0=Monday, 4=Friday
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    weekday = pd.Series(close.index, index=close.index).apply(lambda ts: pd.Timestamp(ts).weekday())
    position = (weekday == long_weekday).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

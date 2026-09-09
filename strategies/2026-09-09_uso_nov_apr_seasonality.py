"""Strategy: Crude oil (USO) November-to-April seasonal long window.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-054):
Per QuantifiedStrategies.com's Crude Oil Trading Strategies guide (visited
this iteration, https://www.quantifiedstrategies.com/crude-oil-trading-strategies/):
"Seasonal peaks usually appear in April, May, and November, while troughs
appear in January and September. (As a matter of fact, most of the gains
have come from the end of November to the end of April.)" This gives a
concrete, testable seasonal calendar window even though the source's own
backtested day-of-week/Friday-seasonality strategy rules are paywalled.

Rationale (source's own framing): crude oil is refined into gasoline and
distillate; seasonal inventory drawdowns/builds track winter heating and
spring driving-season demand ramp-up, producing a systematic price
tailwind from late November (winter heating demand kicks in, inventories
draw down) through late April (pre-driving-season positioning).

Signal logic
------------
- Long USO (or any single equity/ETF symbol passed in) from
  `entry_month`/`entry_day` (default Nov 25) through `exit_month`/
  `exit_day` (default Apr 30) of the following year, flat the rest of the
  year (May through late November).
- No indicators -- pure calendar-date strategy testing the source's
  disclosed seasonal window directly, first crude-oil seasonality
  strategy in this repo (prior entries only tested USO/XLE cross-asset
  momentum gating, not this specific calendar window).

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


def _in_seasonal_window(
    ts: pd.Timestamp, entry_month: int, entry_day: int, exit_month: int, exit_day: int
) -> bool:
    """True if ts falls within the Nov(entry)->Apr(exit) seasonal window,
    which wraps across the calendar-year boundary.
    """
    month, day = ts.month, ts.day
    md = (month, day)
    entry_md = (entry_month, entry_day)
    exit_md = (exit_month, exit_day)

    if entry_md <= exit_md:
        # Window doesn't cross year boundary (not the typical case here).
        return entry_md <= md <= exit_md
    # Window crosses the year boundary (e.g. Nov 25 -> Apr 30).
    return md >= entry_md or md <= exit_md


def generate_signals(
    price_df: pd.DataFrame,
    entry_month: int = 11,
    entry_day: int = 25,
    exit_month: int = 4,
    exit_day: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    in_window = pd.Series(
        [
            _in_seasonal_window(ts, entry_month, entry_day, exit_month, exit_day)
            for ts in close.index
        ],
        index=close.index,
    )
    position = in_window.astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

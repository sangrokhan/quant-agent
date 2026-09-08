"""Strategy: 4-Year Presidential Election Cycle seasonality (US equities).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Yale Hirsch's Stock Trader's Almanac (summarized at
https://www.quantifiedstrategies.com/president-election-cycles/), the US
stock market's performance follows a predictable 4-year pattern tied to the
presidential election cycle: years 1-2 of a president's term (post-election
year and midterm year) tend to be weakest, while year 3 (the pre-election
year) is historically the strongest (S&P 500 up ~12.5% on average in
election years when a sitting president runs for reelection, and the
pre-election year is called "the best year of the cycle"), and year 4
(election year) is the second-best. The behavioral/structural rationale
offered by the source: incumbent administrations emphasize economic
stimulus in the back half of their term to boost re-election odds, while
policy uncertainty and austerity measures cluster in the first half.

Operationalized here as a long-only calendar-based regime filter: be long
QQQ/SPY (or BTC/ETH as a robustness cross-check, though the effect is
specifically a US-political-cycle phenomenon so crypto is not expected to
show it) only during "cycle years" 3 and 4 (pre-election + election year)
of each 4-year US presidential term, flat during cycle years 1 and 2
(post-election + midterm year). US presidential election years are known
in advance (2020, 2024, 2028, ...), so year-in-cycle is a pure calendar
lookup requiring no external data feed beyond the OHLCV timestamp itself.

First presidential-election-cycle seasonality entry in this repo --
distinct from existing intra-year seasonal effects (turn-of-month,
Halloween indicator, January effect, pre-FOMC drift, etc.) since this
operates on a 4-year political cycle rather than an intra-year calendar
cycle.

Interface contract for validators (see validation/validators.py) /
grid_test.py (see validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd

# US presidential election years (year 4 of each cycle). Year-in-cycle for
# any calendar year Y is: ((Y - ELECTION_YEAR) % 4) + 1, where cycle year 4
# is an election year itself (offset 0), cycle year 3 is the pre-election
# year (offset -1 / +3 mod 4), cycle year 2 is the midterm year, cycle
# year 1 is the post-election year.
_ELECTION_YEAR_ANCHOR = 2020  # any known US presidential election year


def _cycle_year(calendar_year: int) -> int:
    """Return 1-4: 1=post-election, 2=midterm, 3=pre-election, 4=election."""
    offset = (calendar_year - _ELECTION_YEAR_ANCHOR) % 4
    # offset 0 -> election year (cycle 4); offset 1 -> post-election (cycle 1)
    # offset 2 -> midterm (cycle 2); offset 3 -> pre-election (cycle 3)
    mapping = {0: 4, 1: 1, 2: 2, 3: 3}
    return mapping[offset]


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    long_cycle_years: tuple = (3, 4),
    trend_window: int = 0,
) -> pd.Series:
    """Long whenever the calendar year's position in the 4-year US
    presidential cycle is in `long_cycle_years` (default: pre-election +
    election year). Optional `trend_window` > 0 adds an SMA trend filter
    (close > SMA(trend_window)) on top of the calendar gate, for a
    robustness variant; 0 disables it (pure calendar-only signal).
    """
    df = _prep(price_df)
    years = df.index.year
    cycle_years = pd.Series(years, index=df.index).map(_cycle_year)
    calendar_ok = cycle_years.isin(long_cycle_years)

    if trend_window and trend_window > 0:
        sma = df["close"].rolling(trend_window).mean()
        trend_ok = df["close"] > sma
        position = (calendar_ok & trend_ok).astype(int)
    else:
        position = calendar_ok.astype(int)

    return position.rename("position")


def generate_returns(
    price_df: pd.DataFrame,
    long_cycle_years: tuple = (3, 4),
    trend_window: int = 0,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(df, long_cycle_years=long_cycle_years, trend_window=trend_window)
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret.rename("returns")

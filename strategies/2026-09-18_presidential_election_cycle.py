"""Strategy: 4-Year US Presidential Election Cycle seasonality (long the
'pre-election year').

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-023):
Per a Google AI-overview synthesis of SoFi/CFA Institute/Modern Wealth
Management/BMO explainers of Yale Hirsch's Presidential Election Cycle
Theory (visited this iteration via browser_exec -- web_search returned
normal results for keyword discovery, no fallback needed there), the
3rd year of a US presidential term (the "pre-election year") has
historically been the strongest of the 4-year cycle for the S&P 500 (source
claims ~78-82% win rate, ~15-17% average annual return since 1928/1950,
vs. ~10% overall average), because an incumbent administration or party
typically pursues expansionary fiscal/monetary policy ahead of the next
election to support re-election odds. The theory's own exact rule: enter
at the start of the pre-election calendar year (year 3 of the 4-year
cycle, i.e. years where (calendar_year - 1) % 4 == 0 given the last US
presidential election year 2024 anchors year 1 = 2025, year 2 = 2026, year
3 = 2027, year 4 = 2028, repeating every 4 years) and exit at year-end (or
hold through the election-year for a milder secondary effect, per source's
own year 4 ~6-8% average). This strategy operationalizes the primary
version: long only during pre-election calendar years, flat otherwise.

First Presidential Election Cycle strategy in this repo (0 prior hits in
strategies_index.jsonl for "presidential cycle"), distinct from all
already-tested short-horizon seasonality strategies (turn-of-month,
Santa Claus rally, day-of-week, pre-holiday effect) via its multi-year
political/fiscal-policy cycle length. Long history requirement (this
theory only makes sense evaluated over 5-8+ full 4-year cycles) tested
here on SPY back to 1995 -- 1995,1999,2003,2007,2011,2015,2019,2023 are
pre-election years under the standard US election calendar (elections in
1996,2000,...,2024).

Interface contract (see validation/validators.py / validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _is_pre_election_year(year: int, election_anchor_year: int = 2024) -> bool:
    """US presidential elections occur every 4 years; election_anchor_year is
    a known election year (2024). The pre-election year is the year
    immediately BEFORE an election year, i.e. (election_anchor_year - year)
    % 4 == 1 for years before the anchor, or equivalently
    (year - (election_anchor_year - 1)) % 4 == 0.
    """
    return (year - (election_anchor_year - 1)) % 4 == 0


def generate_signals(
    price_df: pd.DataFrame,
    election_anchor_year: int = 2024,
    also_hold_election_year: bool = False,
    entry_month: int = 1,
    exit_month: int = 12,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long during the pre-election calendar year (from entry_month through
    exit_month inclusive); optionally also hold through the following
    election year (also_hold_election_year=True) per the source's secondary
    ~6-8%-average-return finding for election years themselves. Flat
    otherwise (mid-term and post-election years).
    """
    df = _prep(price_df)
    idx = df.index
    years = idx.year
    months = idx.month

    pre_election = pd.Series(
        [_is_pre_election_year(int(y), election_anchor_year) for y in years],
        index=idx,
    )
    election_year = pd.Series(
        [_is_pre_election_year(int(y) - 1, election_anchor_year) for y in years],
        index=idx,
    )

    in_window_pre = pre_election & (months >= entry_month) & (
        (months <= exit_month) if exit_month >= entry_month else True
    )
    if also_hold_election_year:
        in_window_election = election_year & (months <= exit_month)
        position = (in_window_pre | in_window_election).astype(int)
    else:
        position = in_window_pre.astype(int)

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

"""Strategy: Intraday-only holding (open->close), excluding Friday sessions.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://blog.harbourfronts.com/2026/04/21/volatility-risk-premium-and-clustering-intraday-vs-overnight-dynamics/
(Relative Value Arbitrage blog, summarizing Papagelis & Dotsis 2024 "The
Variance Risk Premium Over Trading and Non-Trading Periods", SSRN 4954623):
the variance risk premium is significantly NEGATIVE overnight (options
pricing MORE turbulence than what actually shows up overnight -- i.e.
overnight realized moves tend to undershoot implied) but becomes POSITIVE
and often insignificant intraday (realized intraday moves are closer to, or
exceed, what options priced in). The source's own day-of-week finding:
"going long volatility at the open and closing at the close tends to be
profitable on most days, except Fridays" -- i.e. long-volatility-at-open is
NOT profitable on Fridays, implying Friday's intraday session behaves
differently from the other four (likely more mean-reverting / lower
realized move, consistent with pre-weekend de-risking/liquidity effects).

This is the inverse construction: instead of a volatility strategy, this
tests a directional equity ETF strategy -- go long at the open, exit at the
close (capturing ONLY the intraday open-to-close return, flat overnight),
but SKIP Fridays (flat all day) since the source's own finding says Friday's
intraday session doesn't share the same risk-premium dynamic as Mon-Thu.
This is a structurally new signal for this repo: several prior entries test
OVERNIGHT-only holds (2026-09-03-007 family) or full-day-of-week calendar
filters, but none test an INTRADAY-only (open->close) hold with a
day-of-week exclusion filter derived from a volatility-risk-premium paper.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} participation)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, already causal -- the day-of-week filter uses only that
        day's own known calendar date, no look-ahead)
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
    exclude_weekday: int = 4,  # 4 = Friday (Mon=0 ... Sun=6)
) -> pd.Series:
    """Return a {0,1} participation series: 1 = capture today's intraday
    (open -> close) return; 0 = sit out (flat all day).

    exclude_weekday: an integer weekday (0=Mon..6=Sun) to exclude from
    participation. Default 4 (Friday), per the source's disclosed
    day-of-week exception. Set to -1 to disable the filter entirely
    (participate every day) as an unconditional-baseline control arm.
    """
    df = _prep(price_df)
    idx = df.index
    if exclude_weekday is not None and exclude_weekday >= 0:
        weekday = pd.Series(idx.weekday, index=idx)
        position = (weekday != exclude_weekday).astype(int)
    else:
        position = pd.Series(1, index=idx, dtype=int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Intraday-only daily returns: (close[t] / open[t] - 1) * position[t].

    Crypto has no discrete session open/close distinct from the prior
    close (loaders provide a single daily OHLC bar with open ~= prior
    close for continuously-traded markets), so this is tested there mainly
    as a falsification/contrast check, not an assumption the effect
    transfers 1:1.
    """
    df = _prep(price_df)
    position = generate_signals(price_df, **kwargs)
    intraday_ret = (df["close"] / df["open"] - 1.0)
    strat_returns = intraday_ret * position
    strat_returns = strat_returns.fillna(0.0)
    strat_returns.name = "strategy_returns"
    return strat_returns

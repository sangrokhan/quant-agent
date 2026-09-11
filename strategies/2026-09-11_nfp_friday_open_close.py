"""Strategy: NFP-Friday Open-to-Close calendar effect (first Friday of
each month, intraday long only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-085):
Per QuantifiedStrategies.com's "NFP (Non-Farm Payrolls) Trading Strategy"
(https://www.quantifiedstrategies.com/nfp-trading-strategy/, visited this
iteration), the source's own disclosed SPY backtest since 1993: buying at
the open on the day the NFP report is released (first Friday of each
month, 8:30am ET) and selling at the close the same day produced an
average gain of 0.09% per trade -- vs. an average return of ~0% on any
random day -- i.e. a real, if modest, positive intraday drift specifically
on NFP-release Fridays. The source's own bond (TLT) backtest of the same
rule showed a NEGATIVE average return (-0.02%), and the source's own
N-day-holding extension (buy close on report day, sell close N days
later) showed WORSE-than-random returns for the following 1-6 days
(explicitly noted by the source as possibly confounded with "weak
seasonality after the first three trading days of a new month"). The
source's own stated conclusion is skeptical/negative overall ("hard to
conclude... more or less random... never found any edge in trading on
macro numbers") -- this strategy tests the ONE specific sub-claim
(same-day open-to-close SPY drift on first-Fridays) that the source's own
data shows as a real, non-zero effect, rather than the extended N-day
holds the source itself already found weak.

Approximation: exact NFP release dates require an external economic
calendar this repo's data/loaders.py does not provide; the first Friday
of each calendar month is the correct NFP release date in the vast
majority of months (occasional holiday-shift exceptions, e.g. a Monday
holiday pushing the release, are a small, un-modeled minority of months
and are treated as noise here).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position,
        1 only on first-Friday-of-month days)

NOTE: generate_signals here returns a position flag on the SIGNAL day
itself (not shifted), because this is an explicit same-day
open-to-close trade (enter at today's open, exit at today's close) --
unlike every other overnight-hold strategy in this repo, there is
deliberately NO look-ahead-avoiding shift(1) in generate_returns, since
the return computed is the SAME day's open-to-close return, entered and
exited entirely within the signal day (no overnight carry, no reliance
on yesterday's close-derived signal).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _is_first_friday(index: pd.DatetimeIndex) -> pd.Series:
    idx = pd.DatetimeIndex(index)
    is_friday = idx.weekday == 4
    is_first_week = idx.day <= 7
    return pd.Series(is_friday & is_first_week, index=index)


def generate_signals(
    price_df: pd.DataFrame,
) -> pd.Series:
    """Return a {0,1} flag series: 1 on days that are the first Friday of
    their calendar month (NFP-release-day proxy), 0 otherwise. This is a
    same-day intraday trade flag, not an overnight position."""
    df = _prep(price_df)
    flag = _is_first_friday(df.index).astype(int)
    flag.index = df.index
    return flag


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Same-day open-to-close return on first-Friday-of-month days, 0
    otherwise. Deliberately NOT shifted (see module docstring) -- this is
    a same-day open-to-close trade, not a signal-then-hold-next-day rule.
    """
    df = _prep(price_df)
    flag = generate_signals(price_df, **kwargs)
    open_to_close_ret = (df["close"] / df["open"] - 1.0).fillna(0.0)
    strategy_ret = flag.astype(float) * open_to_close_ret
    return strategy_ret

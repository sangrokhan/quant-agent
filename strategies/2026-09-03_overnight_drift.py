"""Strategy: Overnight-return-only holding (close-to-open), flat during the
trading session.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-007),
sourced from https://stoxx.com/when-do-returns-come-from-an-analysis-of-the-overnight-effect-in-equities-trading/
(STOXX blog, Hamish Seegopaul, analyzing EURO STOXX 50 / iShares EUE ETF,
Jan 2016-Oct 2025), which itself cites Boyarchenko, Larsen & Whelan (2023,
"The Overnight Drift", Review of Financial Studies) and Haghani, Ragulin &
Dewey (2024, "Night Moves", Journal of Investment Management). The source's
own numbers: overnight (previous close -> today's open) return was 12.9%
p.a. vs. the ETF's total ~8% p.a., with intraday (open -> close) actually
NEGATIVE at -4.3% p.a.; after 2bp/day round-trip costs, net overnight
return fell to 7.3% p.a. -- still below plain buy-and-hold, per the
source's own honest caveat ("free lunches remain few and far between").

This tests the same close-to-open-only holding pattern on this repo's
universe (SPY/QQQ equity, BTC/USDT/ETH/USDT crypto) with an optional
long-term trend filter (0 = no filter, i.e. every night; >0 = only
participate in the overnight session when the prior close was above its
N-day SMA). Crypto trades 24/7 with no discrete session close/open
boundary equivalent to equities -- treating its once-daily UTC-midnight
bar boundary as a synthetic "close/open" is a deliberate falsification
check, not an assumption the effect transfers.

This is a structurally new signal for this repo: every prior strategy
traded the close-to-close daily bar; this one trades the close-to-open
*sub-daily* window specifically, using each day's `open` and `close`
columns rather than only `close`.

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} participation series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        already causal -- see notes below, no additional 1-day shift needed
        since the trend filter itself already only uses information known
        as of the prior close)
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
    trend_window: int = 0,
) -> pd.Series:
    """Return a {0,1} participation series: 1 = capture the overnight
    (prior close -> today's open) return for this bar; 0 = sit it out.

    trend_window=0 means "always participate" (the source's base-case
    finding); trend_window>0 adds a filter: only participate in tonight's
    overnight session if the prior day's close was above its
    `trend_window`-day SMA (as of the prior close -- no look-ahead).
    """
    df = _prep(price_df)
    close = df["close"]

    if trend_window and trend_window > 0:
        trend_sma = close.rolling(trend_window).mean()
        above_trend = (close > trend_sma).fillna(False)
        # Shift by 1: today's participation decision uses yesterday's
        # close-vs-SMA state (known before tonight's overnight session).
        position = above_trend.shift(1).fillna(False).astype(int)
    else:
        position = pd.Series(1, index=close.index, dtype=int)
        position.iloc[0] = 0  # no prior close available for bar 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Overnight-only daily returns: (open[t] / close[t-1] - 1) * position[t].

    Already causal (position[t] only depends on information known before
    today's open), so no extra 1-day shift is applied here unlike the
    close-to-close strategies elsewhere in this repo.
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    position = generate_signals(price_df, **kwargs)

    prior_close = close.shift(1)
    overnight_ret = (open_ / prior_close - 1.0).fillna(0.0)
    strategy_ret = position * overnight_ret
    return strategy_ret

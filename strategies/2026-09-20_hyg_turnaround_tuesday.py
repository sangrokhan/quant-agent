"""Strategy: HYG (junk bond ETF) day-of-week seasonality -- long Monday close to Tuesday close.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-059):
Per quantifiedstrategies.com's "Junk Bond Trading Strategies: Seasonality,
Backtest, Performance"
(https://www.quantifiedstrategies.com/junk-bond-trading-strategies/,
visited this iteration via browser_exec fallback -- web_search DDGS
backend hit repeated TLS/connection-reset errors this iteration), a
day-of-week backtest on HYG (junk bond ETF) found: "Monday is the weakest
day while Tuesday is the best. This might hint that there is Turnaround
Tuesday effect in junk bonds." (methodology disclosed: buy at close, sell
next day's close, so "Tuesday is the best" means buying Monday's close and
selling Tuesday's close is the best 1-day slot.)

This repo has tested the Turnaround Tuesday effect extensively on
equities/crypto (7+ prior entries, e.g. 2026-09-03-018 rejected plain
version, 2026-09-20-002 accepted Monday-down-conditional version) but
NEVER on HYG or any junk-bond/credit-market ETF specifically. Junk bonds
are documented by the source itself as trending more than stocks (lower
mean-reversion propensity), which could make a day-of-week seasonality
either stronger (less noise to fight) or weaker (seasonality effects
compete against a persistent trend) than in equities -- an empirical
question this repo has not yet tested for this asset class.

Mechanical rule: long HYG from Monday's close to Tuesday's close (1-day
hold), flat all other days. Tests both the UNCONDITIONAL version (matching
the source's own disclosed backtest exactly) and, if that's a near-miss,
this repo's own already-accepted Monday-down-conditional refinement
(2026-09-20-002) as a fallback improvement to try on this new asset.

Source: https://www.quantifiedstrategies.com/junk-bond-trading-strategies/
(day-of-week seasonality table result disclosed in free article body; the
site's own separate undisclosed "junk bond trading strategy... based on a
monthly seasonality" mentioned later in the article is explicitly withheld
by the source ("we don't want to publish the strategy") and is NOT
attempted here.)

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: 1 long/0 flat)
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


def generate_signals(
    price_df: pd.DataFrame,
    require_monday_down: bool = False,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long from Monday's close through Tuesday's close (i.e. position=1 on
    Monday, held into Tuesday, flat otherwise). If `require_monday_down`
    is True, only take the trade when Monday itself was a down day (close
    < previous close) -- mirroring this repo's already-accepted
    Monday-down-conditional refinement (2026-09-20-002) for equities.
    """
    df = _prep(price_df)
    close = df["close"]
    weekday = close.index.dayofweek  # Monday=0, Tuesday=1

    is_monday = pd.Series(weekday == 0, index=close.index)
    monday_down = close < close.shift(1)

    entry_monday = is_monday
    if require_monday_down:
        entry_monday = entry_monday & monday_down.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    for i in range(len(close)):
        if bool(entry_monday.iloc[i]):
            position.iloc[i] = 1
            if i + 1 < len(close):
                position.iloc[i + 1] = 1
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

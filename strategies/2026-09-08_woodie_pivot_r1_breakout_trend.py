"""Strategy: Woodie's Pivot Point R1 breakout, trend-filtered.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Swoopr's "Woodie Pivot Points Explained: Formula, Levels, and Signals"
(https://www.getswoopr.com/learn/technical-analysis/indicators/woodie-pivot-points/),
Woodie's pivot gives the prior period's close DOUBLE weight versus the
standard (H+L+C)/3 pivot:

    PP = (High + Low + 2*Close) / 4
    R1 = (2*PP) - Low
    S1 = (2*PP) - High
    R2 = PP + (High - Low)
    S2 = PP - (High - Low)

where High/Low/Close are the prior completed period's values (here, prior
daily bar -- this repo trades daily bars, so each day's Woodie levels are
built from the previous day's OHLC). The source describes R1/R2 as "areas
where an advance might stall, reverse, or need to break through with
conviction (a 'breakout' read) to keep extending" -- i.e. closing above R1
signals a conviction breakout through the first reaction zone.

We operationalize the breakout read as a testable rule: long entry when
close breaks above the day's R1 level AND close is above a trend_window-day
SMA (trend filter, since the source explicitly warns pivot levels alone
don't account for trend and "a strong trending market can push straight
through R2... the same way it can push through standard pivot levels" --
so we require the broader trend context to already be favorable, rather
than trading the breakout blind). Exit when close falls back below the
day's PP (loses the pivot's bullish-bias level) or after a max_hold_days
time-stop.

Distinct from all 5 prior "pivot point"-tagged entries in this repo, none
of which use Woodie's double-close-weighted variant specifically (grep of
"woodie" in strategies_index.jsonl surfaces only Woodie's CCI, an unrelated
oscillator by the same trader, not this pivot-point construction). First
Woodie Pivot Point (S/R breakout) entry in this repo.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Position-weighted daily strategy returns (no transaction costs).
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} long/flat position series aligned to price_df.index.
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
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # Woodie pivot levels for "today" are built from yesterday's completed bar.
    prior_high = high.shift(1)
    prior_low = low.shift(1)
    prior_close = close.shift(1)

    pp = (prior_high + prior_low + 2 * prior_close) / 4.0
    r1 = (2 * pp) - prior_low

    sma_trend = close.rolling(trend_window).mean()

    entry = (close > r1) & (close > sma_trend)
    exit_pp = close < pp

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    valid_start_candidates = [pp.first_valid_index(), sma_trend.first_valid_index()]
    valid_start_candidates = [c for c in valid_start_candidates if c is not None]
    valid_start = max(valid_start_candidates) if valid_start_candidates else None
    for i in range(len(close)):
        if valid_start is not None and close.index[i] < valid_start:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(exit_pp.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
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

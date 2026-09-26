"""Strategy: First-200MA-Cross-Under Regime Timing (single-symbol proxy).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Per Cesar Alvarez's "The 30% Selloff Signal: What History Tells Us About
Market Recoveries" (https://alvarezquanttrading.com/blog/the-30-selloff-signal-what-history-tells-us-about-market-recoveries/,
read via browser_exec): the FIRST day the S&P 500 index closes under its
own 200-day SMA after having been above it for 6+ months tends to precede
above-average subsequent returns (source's own finding: 3/6/12-month
forward returns after this trigger were higher than the unconditional
average, strongest when combined with elevated cross-sectional breadth
weakness -- e.g. >10% of stocks 30%+ off their 52-week high).

The source's own breadth statistic (% of Russell 3000/S&P 500 CONSTITUENT
stocks 30%+ off their own 52-week high) requires cross-sectional
multi-stock data this repo's single-symbol `generate_returns_fn` contract
cannot support. This strategy instead uses a SINGLE-SYMBOL PROXY for that
breadth-weakness idea: the primary asset's OWN percentage distance below
its own trailing 52-week (252-day) high, as a substitute regime-severity
gauge, combined with the source's exact "first 200MA cross-under after 6+
months above" trigger mechanism (fully implementable on single-symbol
OHLCV).

First "first-cross-after-sustained-uptrend" 200MA regime-timing strategy
in this repo (distinct from every other plain SMA(200) trend-following
strategy already tested, which uses a continuous state -- "invested
whenever price>SMA200" -- rather than a ONE-TIME EVENT trigger fired only
on the specific day of a fresh cross-under after 6+ months of being above).

Signal logic
------------
- sma200 = close.rolling(200).mean()
- above = close > sma200
- "sustained uptrend" = above has been True for >= min_months_above*21
  trading days immediately before the cross (approximating 6 calendar
  months as ~126 trading days).
- trigger day t: above(t-1)==True, above(t)==False, AND the trailing
  streak of above==True immediately preceding t is >= min_months_above*21.
- own_drawdown(t) = 1 - close(t)/rolling_max(close, 252)(t) (proxy for the
  source's cross-sectional breadth-weakness severity gauge).
- On a trigger day, go long for `hold_days` trading days (approximating
  the source's 3/6/12-month forward-return windows; parameterized).
  Optionally require own_drawdown(t) >= min_drawdown_pct (severity gate,
  approximating the source's "buckets" finding that a bigger sell-off
  produces a stronger subsequent-return edge).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1})
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    min_months_above: int = 6,
    hold_days: int = 126,
    min_drawdown_pct: float = 0.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    sma200 = close.rolling(200).mean()
    above = (close > sma200).fillna(False)

    rolling_max_252 = close.rolling(252, min_periods=1).max()
    own_drawdown = 1.0 - (close / rolling_max_252)

    min_days_above = min_months_above * 21

    position = pd.Series(0, index=close.index, dtype=int)
    hold_remaining = 0

    # Precompute the "streak of True immediately before" length at each bar.
    above_streak = pd.Series(0, index=close.index, dtype=int)
    streak = 0
    for i in range(n):
        above_streak.iloc[i] = streak
        if bool(above.iloc[i]):
            streak += 1
        else:
            streak = 0

    for i in range(n):
        if hold_remaining > 0:
            position.iloc[i] = 1
            hold_remaining -= 1
            continue
        if i == 0:
            continue
        is_cross_under = bool(above.iloc[i - 1]) and not bool(above.iloc[i])
        sustained = above_streak.iloc[i] >= min_days_above
        severe_enough = own_drawdown.iloc[i] >= min_drawdown_pct
        if is_cross_under and sustained and severe_enough:
            position.iloc[i] = 1
            hold_remaining = hold_days - 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    min_months_above: int = 6,
    hold_days: int = 126,
    min_drawdown_pct: float = 0.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        min_months_above=min_months_above,
        hold_days=hold_days,
        min_drawdown_pct=min_drawdown_pct,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret.fillna(0.0)

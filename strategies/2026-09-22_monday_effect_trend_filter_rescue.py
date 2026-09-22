"""Strategy: Monday Effect avoidance + SMA trend filter (rescue of 2026-09-22-069).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-070):
Direct rescue attempt for this same cron trigger's prior rejection
2026-09-22-069 (Monday Effect avoidance, decisive Sharpe+MDD fail on both
QQQ and SPY -- being long ~4/5 trading days made it essentially
"buy-and-hold minus Mondays" with MDD nearly identical to unfiltered
buy-hold). That report's own suggested next step: use the Monday-avoidance
filter as a SECONDARY overlay within an already-selective trend-following
entry, rather than as the sole standalone signal, since the modest
day-of-week edge should tip an already-marginal strategy rather than carry
the whole Sharpe/MDD burden alone. This iteration implements exactly that:
combine the day-of-week filter (flat Mondays) with the standard
close>SMA(trend_window) uptrend gate (this repo's most common baseline
trend filter, used in >50 other strategies here) as the PRIMARY selectivity
mechanism, with the Monday-avoidance as a secondary refinement on top.

Signal logic
------------
- Long entry/hold: close > SMA(trend_window) (primary trend gate, provides
  the real drawdown protection the pure calendar version lacked) AND the
  bar's day-of-week is NOT Monday (secondary Monday-effect refinement).
- Flat when either condition fails (downtrend OR Monday).
- No time-stop needed -- flips daily off the two conditions.
- Long-only (no short per SAFETY.md scope).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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
    trend_window: int = 100,
    avoid_weekdays: tuple = (0,),
) -> pd.Series:
    df = _prep(price_df)
    idx = df.index
    close = df["close"]
    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False)

    dow = idx.tz_localize(None).dayofweek if idx.tz is not None else idx.dayofweek
    avoided = pd.Series(dow, index=idx).isin(list(avoid_weekdays))

    position = pd.Series((uptrend & (~avoided)).astype(int), index=idx)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    avoid_weekdays: tuple = (0,),
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(df, trend_window=trend_window, avoid_weekdays=avoid_weekdays)
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

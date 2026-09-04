"""Strategy: Internal Bar Strength (IBS) mean reversion, with 200-SMA trend
proximity filter and a max-holding-period safety exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-089):
IBS = (Close - Low) / (High - Low) measures where a bar's close sits within
its own high-low range. Per quantifiedstrategies.com's published SPY/QQQ
backtests (1993-present): buying on close when IBS < 0.2 (close near the
day's low -> intraday panic/oversold) and exiting on close when IBS rises
above 0.8 (close near the day's high -> overbought/reversion complete) is a
short-horizon (avg hold ~a few days) mean-reversion edge, historically
CAGR-beating buy-and-hold with Sharpe ~1.7 for the refined IBS-only exit
variant. The source also notes the edge degrades if price is far above its
200-day trend (overextended), so this variant adds an optional
`trend_band_pct` filter: only enter when close is within `trend_band_pct` of
the 200-SMA (not more than X% above it), per the source's own finding that
capping "how far above the 200-SMA" improves quality. A `max_hold_days`
safety exit prevents indefinite holds if IBS never crosses back above the
exit threshold.

Signal logic
------------
- Entry: IBS(t) < ibs_entry (default 0.2) AND close(t) <= sma200(t) * (1 +
  trend_band_pct) [trend filter, skip if trend_band_pct is None]
- Exit: IBS(t) > ibs_exit (default 0.8), OR max_hold_days elapsed since
  entry (whichever first)
- Long-only, one position at a time, no pyramiding.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _compute_ibs(df: pd.DataFrame) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    rng = (high - low).replace(0, np.nan)
    ibs = (close - low) / rng
    return ibs.fillna(0.5)


def generate_signals(
    price_df: pd.DataFrame,
    ibs_entry: float = 0.2,
    ibs_exit: float = 0.8,
    trend_band_pct: float = 0.05,
    sma_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    ibs = _compute_ibs(df)
    sma = close.rolling(sma_window, min_periods=max(20, sma_window // 5)).mean()

    if trend_band_pct is not None:
        trend_ok = close <= sma * (1.0 + trend_band_pct)
        trend_ok = trend_ok.fillna(False)
    else:
        trend_ok = pd.Series(True, index=df.index)

    entry_trigger = (ibs < ibs_entry) & trend_ok
    exit_trigger = ibs > ibs_exit

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            if bool(exit_trigger.iloc[i]) or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    ibs_entry: float = 0.2,
    ibs_exit: float = 0.8,
    trend_band_pct: float = 0.05,
    sma_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        ibs_entry=ibs_entry,
        ibs_exit=ibs_exit,
        trend_band_pct=trend_band_pct,
        sma_window=sma_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

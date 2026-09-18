"""Strategy: CCI Correction (StockCharts) -- weekly-bias / daily-correction
dual-timeframe CCI mean-reversion-into-trend system.

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
Per StockCharts.com ChartSchool's "CCI Correction"
(https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/cci-correction,
read via browser_exec fallback after web_search's DDGS backend could not
extract page content; strategy attributed to Donald Lambert's Commodity
Channel Index guidelines): a genuinely dual-timeframe mean-reversion-INTO-
trend system with three explicit steps:
  1. BIAS: on the WEEKLY chart, a 26-period CCI surge above +100 sets a
     bullish trading bias (persists until a surge below -100 flips it
     bearish, and vice versa) -- source's own worked example uses 26-week
     CCI ("represents six months").
  2. CORRECTION: on the DAILY chart, wait for a counter-trend pullback --
     while bias is bullish, a daily CCI plunge below -100 is a pullback
     worth watching (the opposite for bearish bias).
  3. REVERSAL: the daily CCI subsequently surging back above the ZERO line
     (not all the way back to +100) confirms the pullback has reversed and
     the bigger trend is resuming -- this is the actual entry trigger.

This repo's data/loaders.py only provides daily OHLCV, so the "weekly"
timeframe is approximated by resampling the daily close series to weekly
bars internally (last close of each ISO week) to compute the genuinely
longer-period CCI, then forward-filling that weekly-bias signal onto the
daily index -- a faithful, no-look-ahead reproduction of the source's own
dual-timeframe design (the weekly bias is only known using CLOSED weekly
bars, shifted by one week to avoid look-ahead into the still-forming
current week). Exit: bias flips (trend reversal), or a max_hold_days
time-stop (source's own examples show correction-to-reversal cycles lasting
weeks to months without an explicit numeric exit, so a time-stop is this
repo's own conservative backstop).

First strategy in this repo using a genuine RESAMPLED WEEKLY indicator to
set a persistent regime bias combined with a DAILY oscillator's zero-line
recovery (not its own +100/-100 extreme) as the actual entry trigger --
distinct from every prior CCI entry (49 in this repo) which all operate on
a single daily-bar timeframe.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cci(df: pd.DataFrame, window: int) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    sma_tp = typical_price.rolling(window).mean()
    import numpy as np

    mean_dev = typical_price.rolling(window).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    )
    return (typical_price - sma_tp) / (0.015 * mean_dev.replace(0, float("nan")))


def _weekly_bias(df: pd.DataFrame, weekly_window: int = 26) -> pd.Series:
    """Resample to weekly bars, compute CCI, derive persistent bias
    (+1 bullish, -1 bearish, 0 unknown), shift by 1 week to avoid
    look-ahead, then forward-fill back onto the daily index."""
    weekly = df.resample("W").agg(
        {"high": "max", "low": "min", "close": "last"}
    ).dropna()
    weekly_cci = _cci(weekly, weekly_window)

    bias = pd.Series(0, index=weekly.index, dtype=int)
    state = 0
    for i in range(len(weekly)):
        val = weekly_cci.iloc[i]
        if pd.notna(val):
            if val > 100:
                state = 1
            elif val < -100:
                state = -1
        bias.iloc[i] = state

    # Shift by 1 week: today's daily bar may only use LAST week's fully
    # closed bias, not the still-forming current week's.
    bias = bias.shift(1)
    daily_bias = bias.reindex(df.index.union(bias.index)).sort_index().ffill()
    return daily_bias.reindex(df.index).fillna(0)


def _core(
    price_df: pd.DataFrame,
    weekly_window: int = 26,
    daily_window: int = 26,
    extreme_level: float = 100.0,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    daily_cci = _cci(df, daily_window)
    bias = _weekly_bias(df, weekly_window)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    awaiting_pullback = False
    hold_days = 0
    for i in range(len(df)):
        b = bias.iloc[i]
        c = daily_cci.iloc[i]
        if in_pos:
            hold_days += 1
            if b <= 0 or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                awaiting_pullback = False
            else:
                position.iloc[i] = 1
        else:
            if b > 0:
                if pd.notna(c) and c < -extreme_level:
                    awaiting_pullback = True
                if awaiting_pullback and pd.notna(c) and c > 0:
                    in_pos = True
                    hold_days = 0
                    awaiting_pullback = False
                    position.iloc[i] = 1
            else:
                awaiting_pullback = False
    return position


def generate_signals(
    price_df: pd.DataFrame,
    weekly_window: int = 26,
    daily_window: int = 26,
    extreme_level: float = 100.0,
    max_hold_days: int = 40,
) -> pd.Series:
    return _core(price_df, weekly_window, daily_window, extreme_level, max_hold_days)


def generate_returns(
    price_df: pd.DataFrame,
    weekly_window: int = 26,
    daily_window: int = 26,
    extreme_level: float = 100.0,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = _core(df, weekly_window, daily_window, extreme_level, max_hold_days)
    daily_ret = close.pct_change().fillna(0.0)
    return daily_ret * position.shift(1).fillna(0)

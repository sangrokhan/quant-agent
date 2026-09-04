"""Strategy: Ultimate Oscillator pullback-in-trend (mid-zone dip + price trigger).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-134):
The Ultimate Oscillator (Larry Williams, blends buying-pressure/true-range
ratios across 7/14/28-period windows weighted 4:2:1) is used here per
[trendsandbreakouts.com](https://trendsandbreakouts.com/ultimate-oscillator)'s
own "pullback trading" rule set (distinct from the simpler 30/70
threshold-crossover already rejected in this repo as id 2026-09-04-050):
"Trend filter: trade long only when price is above your trend filter...
Pullback long entry: wait for Ultimate Oscillator to dip toward the mid
zone then turn up, enter on a price trigger like a break above the prior
day high." Operationalized: (1) close above a trend_window SMA (trend
filter), (2) UO dips to/below a mid_zone_low threshold then shows 2
consecutive rising closes (the source's own suggested "turn" definition,
"require two consecutive higher closes in the oscillator after a
pullback"), (3) entry triggers on close breaking above the prior day's
high. Exit: close breaks below the prior swing low (source's
"exit... when price breaks structure against you"), approximated as a
close below a short lookback rolling low, OR a max_hold_days time-stop.

Signal logic
------------
- trend_window: SMA period for the directional trend filter (default 100).
- mid_zone_low: UO threshold below which a "pullback" is registered
  (default 45, source's "mid zone").
- swing_lookback: lookback window for the prior-day-high entry trigger
  and prior-swing-low exit trigger (default 1 for prior-day-high entry,
  a longer rolling-low window for the exit).
- exit_lookback: rolling-low window for the structural exit level
  (default 10).
- Long entry: close > trend SMA AND UO touched <= mid_zone_low within
  the last 5 bars AND UO shows 2 consecutive rising closes AND close
  breaks above the prior bar's high.
- Exit: close < rolling exit_lookback-day low (excluding current bar),
  OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ultimate_oscillator(df: pd.DataFrame, n1: int = 7, n2: int = 14, n3: int = 28) -> pd.Series:
    close = df["close"]
    low = df["low"]
    high = df["high"]
    prev_close = close.shift(1)

    bp = close - pd.concat([low, prev_close], axis=1).min(axis=1)
    tr = pd.concat([high, prev_close], axis=1).max(axis=1) - pd.concat([low, prev_close], axis=1).min(axis=1)

    avg1 = bp.rolling(n1).sum() / tr.rolling(n1).sum()
    avg2 = bp.rolling(n2).sum() / tr.rolling(n2).sum()
    avg3 = bp.rolling(n3).sum() / tr.rolling(n3).sum()

    uo = 100 * (4 * avg1 + 2 * avg2 + 1 * avg3) / 7
    return uo


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    mid_zone_low: float = 45.0,
    exit_lookback: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    uo = _ultimate_oscillator(df)
    trend_sma = close.rolling(trend_window).mean()
    trend_ok = close > trend_sma

    dipped_recently = (uo <= mid_zone_low).rolling(5).max().astype(bool)
    two_rising = (uo > uo.shift(1)) & (uo.shift(1) > uo.shift(2))
    price_trigger = close > high.shift(1)

    entry_signal = trend_ok & dipped_recently & two_rising & price_trigger

    exit_level = close.shift(1).rolling(exit_lookback).min()
    exit_signal = close < exit_level

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = bool(exit_signal.iloc[i]) if pd.notna(exit_signal.iloc[i]) else False
            if exit_now or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entry_now = bool(entry_signal.iloc[i]) if pd.notna(entry_signal.iloc[i]) else False
            if entry_now:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    mid_zone_low: float = 45.0,
    exit_lookback: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        trend_window=trend_window,
        mid_zone_low=mid_zone_low,
        exit_lookback=exit_lookback,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

"""Strategy: Pocket Pivot (O'Neil/Gil Morales institutional-accumulation
volume signature), long entry with an ATR-scaled pivot-low stop exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-012):
Per LuxAlgo's "Pocket Pivot" indicator page
(https://www.luxalgo.com/library/indicator/pocket-pivot/, read via
browser_exec this iteration; confirmed by multiple independent sources
found via Google search fallback -- ChartMill, TradingView community
scripts, and the original Gil Morales/O'Neil "OWL" methodology): a
"pocket pivot" day is an up-close day whose volume exceeds the HIGHEST
volume of any DOWN day over the trailing `down_day_lookback` (default 10)
sessions -- a volume signature that historically flags institutional
accumulation happening quietly inside a base, before an obvious breakout.
LuxAlgo's own "clean build" adds constructive-context filters: the pivot
day's close must be above a slow SMA (uptrend context, avoiding extended or
downtrending prints), and the day's low must be within a proximity band of
either the fast or slow SMA (avoiding chasing an already-extended move).

This is the FIRST Pocket Pivot strategy in this repo (0 prior entries) --
a genuinely distinct volume-signature construction from every other
volume-based strategy already tested (OBV, CMF, MFI, Klinger, VPT, PVT,
Force Index, BVC/VPIN, etc., none of which use a "beats the max down-day
volume in a trailing window" comparison specifically).

Signal logic
------------
- Pivot day: close > close.shift(1) (up day) AND volume > the max volume
  among the trailing `down_day_lookback` down-days (days where
  close < close.shift(1)).
- Constructive-context filters (both applied, per LuxAlgo's clean build):
  - Uptrend filter: close > SMA(slow_window).
  - MA support filter: the day's low is within `support_proximity_pct` of
    either SMA(fast_window) or SMA(slow_window), while close still holds
    above the slow SMA.
- Long entry on a qualifying pocket pivot day's close.
- Exit: close falls below that pivot day's own low (the source's classical
  "Pivot Day Low Stop" exit reference), or a max_hold_days time-stop
  backstop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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
    down_day_lookback: int = 10,
    fast_window: int = 10,
    slow_window: int = 50,
    support_proximity_pct: float = 0.02,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    volume = df["volume"]

    is_up_day = close > close.shift(1)
    is_down_day = close < close.shift(1)
    down_day_volume = volume.where(is_down_day)
    max_down_volume = down_day_volume.rolling(down_day_lookback, min_periods=1).max()
    volume_rule = is_up_day & (volume > max_down_volume.shift(1))

    sma_fast = close.rolling(fast_window).mean()
    sma_slow = close.rolling(slow_window).mean()
    uptrend_filter = close > sma_slow

    near_fast = (low - sma_fast).abs() / sma_fast <= support_proximity_pct
    near_slow = (low - sma_slow).abs() / sma_slow <= support_proximity_pct
    support_filter = (near_fast | near_slow) & uptrend_filter

    pocket_pivot = volume_rule & uptrend_filter & support_filter
    pivot_low = low.where(pocket_pivot)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = None
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(close.iloc[i] < stop_level) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                stop_level = None
                continue
            position.iloc[i] = 1
        else:
            if bool(pocket_pivot.iloc[i]):
                in_position = True
                entry_idx = i
                stop_level = float(pivot_low.iloc[i])
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

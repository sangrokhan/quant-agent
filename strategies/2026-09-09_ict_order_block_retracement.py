"""Strategy: ICT-style bullish Order Block retracement entry.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Journali.io's "ICT Order Blocks" strategy page
(https://journali.io/strategies/ict-order-blocks), an institutional "order
block" (OB) is the last opposing-color candle immediately before a strong
impulsive ("displacement") move. Price frequently retraces back into that
candle's range before continuing in the displacement direction, because the
zone marks where large participants built their position. The source's own
backtest reports raw (unfiltered) order-block entries at 56% win rate, and
filtered entries (requiring a genuinely strong displacement + fresh/untested
OB + trading with the higher-timeframe trend) at 61% win rate with average
winners of 2.1R.

Operationalized on daily OHLCV bars (first order-block-family strategy in
this repo):
    1. Displacement bar: a bullish daily bar whose (close - open) exceeds
       `displacement_mult` times the `atr_window`-day ATR (a genuinely
       "strong, fast" move per the source's own definition).
    2. Order block: the last BEARISH (close < open) daily bar immediately
       before that displacement bar. Its [low, high] range is the OB zone.
    3. Higher-timeframe trend filter: only take the OB if close > SMA(trend_window)
       at the time of the displacement (source: "must be trading in the
       direction of the higher timeframe trend").
    4. Entry: within `lookback_window` bars after the OB forms, if price
       retraces back down into the OB zone (low <= close <= high), enter
       long at that close.
    5. Exit: displacement bar's high as profit target, OB's low as a stop,
       or `max_hold_days` time-stop -- whichever comes first (position-based,
       no separate order-management engine; approximated here via a
       vectorized position series consumed by generate_returns).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    displacement_mult: float = 1.5,
    atr_window: int = 14,
    trend_window: int = 50,
    lookback_window: int = 10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series for the bullish order-block
    retracement strategy described in the module docstring."""
    df = _prep(price_df)
    close, open_, high, low = df["close"], df["open"], df["high"], df["low"]
    n = len(df)

    atr = _atr(df, atr_window)
    sma = close.rolling(trend_window, min_periods=trend_window).mean()

    is_bullish = close > open_
    is_bearish = close < open_
    body = (close - open_)

    displacement = is_bullish & (body > displacement_mult * atr) & (close > sma)

    position = pd.Series(0, index=df.index, dtype=int)

    disp_idx = np.where(displacement.fillna(False).values)[0]
    active_end = -1  # index up to which we're already holding a position
    for di in disp_idx:
        if di < 1:
            continue
        # Order block = last bearish bar before the displacement bar.
        ob_i = None
        j = di - 1
        min_search = max(0, di - 5)  # search a small window immediately before
        while j >= min_search:
            if is_bearish.iloc[j]:
                ob_i = j
                break
            j -= 1
        if ob_i is None:
            continue

        ob_low = low.iloc[ob_i]
        ob_high = high.iloc[ob_i]
        target = high.iloc[di]

        # Look for a retracement back into the OB zone within lookback_window
        # bars after the displacement bar.
        entry_i = None
        search_end = min(n - 1, di + lookback_window)
        for k in range(di + 1, search_end + 1):
            c = close.iloc[k]
            if ob_low <= c <= ob_high:
                entry_i = k
                break
        if entry_i is None or entry_i <= active_end:
            continue

        # Hold from entry until target/stop/time-stop, whichever comes first.
        exit_i = min(n - 1, entry_i + max_hold_days)
        for m in range(entry_i, min(n, entry_i + max_hold_days + 1)):
            if close.iloc[m] >= target or close.iloc[m] <= ob_low:
                exit_i = m
                break
        else:
            exit_i = min(n - 1, entry_i + max_hold_days)

        position.iloc[entry_i:exit_i + 1] = 1
        active_end = exit_i

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret

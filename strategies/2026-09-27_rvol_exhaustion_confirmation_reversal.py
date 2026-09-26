"""Strategy: RVOL Exhaustion-Climax Reversal with delayed confirmation candle.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-004):
Per a Google AI-overview synthesis of ChartSchool/TradeAlgo/ChartsWatcher
sources on "Relative Volume (RVOL) spike price reversal" (RVOL = current
volume / rolling N-bar average volume): a mature downtrend making a new
N-bar low, accompanied by an exhaustion spike bar with RVOL >= 4.0
(400%+ of normal volume) and an unusually large price range, marks a
"selling climax". The source's own disclosed 3-step entry timing is
distinctive vs. this repo's many prior climax/exhaustion entries (which
all enter on the SAME bar as the climax spike or the very next bar): do
NOT enter on the spike bar itself; wait for a SEPARATE subsequent
confirmation bar to close in the opposite (bullish) direction; THEN enter
at the open of the bar AFTER that confirmation bar (i.e. climax bar (day
0) -> confirmation bar (day 1, must close > its own open) -> entry at
open of day 2). Stop-loss set 1.0-1.5% beyond the climax bar's own
extreme low (not an ATR multiple or moving-average cross, the source's
own specific stop placement).

This repo's existing climax/exhaustion-reversal family (e.g. 2026-09-16-085
Selling-Climax Wyckoff, 2026-09-22-104 Capitulation-Reversal RSI+volume,
2026-09-06-157/2026-09-08-126 Volume-Climax variants) all enter on the
climax bar itself or the immediately-following bar with no independent
confirmation-candle requirement, and use RVOL thresholds of 1.5-2.5x, not
this source's explicit 4.0x. This is the first strategy in this repo
combining: (a) the source's specific >=4.0x RVOL threshold, (b) a
mandatory separate confirmation-candle bar (not same-bar or immediate-next
entry), and (c) a fixed percentage stop beyond the climax bar's extreme
(not ATR-based or MA-cross-based).

Signal logic
------------
- climax_bar[t]: close[t] <= rolling_low(t, lookback) (new N-bar low) AND
  RVOL[t] = volume[t] / rolling_mean(volume, vol_window)[t-1... t] >=
  rvol_threshold AND (high[t]-low[t]) >= range_mult * rolling ATR (large
  range bar).
- confirmation_bar[t+1]: close[t+1] > open[t+1] (bullish close on the very
  next bar after the climax bar).
- entry at open[t+2] (the bar AFTER the confirmation bar).
- stop-loss: climax bar's own low * (1 - stop_pct); exit if any subsequent
  close falls below this level.
- take-profit / time exit: close >= entry_close * (1 + target_pct), or a
  max_hold_days time-stop, whichever comes first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
"""

from __future__ import annotations

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
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window, min_periods=window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 20,
    vol_window: int = 20,
    rvol_threshold: float = 4.0,
    range_mult: float = 1.5,
    atr_window: int = 14,
    stop_pct: float = 0.015,
    target_pct: float = 0.05,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    open_ = df["open"]
    volume = df["volume"]

    rolling_low = low.rolling(lookback, min_periods=lookback).min()
    avg_volume = volume.rolling(vol_window, min_periods=vol_window).mean().shift(1)
    rvol = volume / avg_volume
    atr = _atr(df, atr_window)
    bar_range = high - low

    climax_bar = (
        (close <= rolling_low)
        & (rvol >= rvol_threshold)
        & (bar_range >= range_mult * atr)
    ).fillna(False)

    confirm_bar = (close > open_).fillna(False)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)

    in_position = False
    entry_idx = 0
    entry_close = None
    stop_level = None

    i = 0
    while i < n:
        if in_position:
            held = i - entry_idx
            hit_stop = bool(low.iloc[i] <= stop_level)
            hit_target = bool(close.iloc[i] >= entry_close * (1 + target_pct))
            if hit_stop or hit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                i += 1
                continue
            position.iloc[i] = 1
            i += 1
            continue

        # look for a climax bar at i, confirmation at i+1, entry at i+2
        if climax_bar.iloc[i] and i + 2 < n and confirm_bar.iloc[i + 1]:
            entry_i = i + 2
            in_position = True
            entry_idx = entry_i
            entry_close = close.iloc[entry_i]
            stop_level = low.iloc[i] * (1 - stop_pct)
            position.iloc[entry_i] = 1
            i = entry_i + 1
            continue
        i += 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

"""Strategy: Golden Cross Breakout with post-cross window + volume
confirmation (Ken Calhoun, TASC Mar 2017).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-141):
Per Ken Calhoun's "Golden Cross Breakouts" (TASC Mar 2017; TradeStation
EasyLanguage code disclosed at
https://traders.com/Documentation/FEEDbk_docs/2017/03/TradersTips.html),
the classic 50/200-day SMA golden cross (already tested plain in this repo,
2026-09-03-021/2026-09-04-074) is refined with THREE additional
confirmation layers the source discloses: (1) after the golden cross fires,
an "EntryOK" flag stays armed only for max_bars_since_cross bars, or until
the fast MA crosses back under the slow MA (source's own state-machine
logic -- "if BarsSinceCross > MaxBarsSinceCross ... EntryOK = false"),
(2) the actual entry requires close to break out ABOVE the highest high of
the trailing breakout_lookback bars measured AT THE MOMENT of the golden
cross (source: "BreakOutPrice = Highest(High, BreakoutLookBack)" fixed at
cross time, not a rolling breakout), and (3) volume on the breakout bar
must exceed volume_mult_required times its own fast_length-day average
(source's own "BarVolume >= AvgVolume * VolumeMultRequired"). Exit: close
crosses below the fast MA (source's own rule). This is a genuinely
different mechanical trigger from the plain golden cross -- it requires the
cross AND a subsequent breakout-with-volume confirmation within a limited
window, not just the moving-average state itself.

Signal logic
------------
- fast_avg = SMA(close, fast_length); slow_avg = SMA(close, slow_length).
- golden_cross = fast_avg crosses over slow_avg.
- On a golden_cross bar, record breakout_price = rolling max(high,
  breakout_lookback) AS OF THAT BAR (frozen, not updated each subsequent
  bar).
- entry_armed persists from the cross bar for up to max_bars_since_cross
  bars, and is disarmed early if fast_avg crosses back under slow_avg.
- avg_volume = SMA(volume, fast_length).
- Entry (long): entry_armed AND close > breakout_price (frozen) AND
  volume >= avg_volume * volume_mult_required.
- Exit: close crosses below fast_avg (source's own rule), OR
  max_hold_days time-stop.
- Flat otherwise.

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


def generate_signals(
    price_df: pd.DataFrame,
    fast_length: int = 50,
    slow_length: int = 200,
    max_bars_since_cross: int = 10,
    breakout_lookback: int = 20,
    volume_mult_required: float = 1.5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(0.0, index=df.index)

    fast_avg = close.rolling(fast_length).mean()
    slow_avg = close.rolling(slow_length).mean()
    golden_cross = (fast_avg > slow_avg) & (fast_avg.shift(1) <= slow_avg.shift(1))
    death_cross = (fast_avg < slow_avg) & (fast_avg.shift(1) >= slow_avg.shift(1))

    rolling_high = high.rolling(breakout_lookback).max()
    avg_volume = volume.rolling(fast_length).mean()

    n = len(df)
    entry_armed = pd.Series(False, index=df.index)
    breakout_price = pd.Series(float("nan"), index=df.index)

    cur_armed = False
    cur_bars_since_cross = 0
    cur_breakout_price = float("nan")

    for i in range(n):
        if bool(golden_cross.iloc[i]):
            cur_armed = True
            cur_bars_since_cross = 0
            cur_breakout_price = rolling_high.iloc[i]
        elif cur_armed:
            cur_bars_since_cross += 1
            if cur_bars_since_cross > max_bars_since_cross or bool(death_cross.iloc[i]):
                cur_armed = False
        entry_armed.iloc[i] = cur_armed
        breakout_price.iloc[i] = cur_breakout_price

    volume_ok = volume >= (avg_volume * volume_mult_required)
    entry = entry_armed & (close > breakout_price).fillna(False) & volume_ok.fillna(False)
    exit_fast_flip = close < fast_avg

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_fast_flip.iloc[i]) or held >= max_hold_days:
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

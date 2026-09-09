"""Strategy: Volume RSI (VoRSI) 50-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-098):
Per QuantStrategy.io's "How to Trade with Volume RSI Indicator" article
(https://quantstrategy.io/blog/how-to-trade-with-volume-rsi-indicator/):
Volume RSI (VoRSI) applies the classic RSI formula to UP/DOWN VOLUME
instead of up/down price changes: VoRSI = 100 - 100/(1 + VoRS), where
VoRS is the ratio of average up-volume to average down-volume over a
lookback window (up-volume = volume on days the close rose; down-volume
= volume on days the close fell). VoRSI oscillates 0-100 around a 50
midline: above 50 means bullish volume dominates, below 50 means bearish
volume dominates. Source's exact trading rule: "traders can buy when the
indicator moves above the 50% line from below and sell when the
indicator drops beneath the 50% line from above."

First Volume RSI (RSI-of-volume-direction, distinct from OBV/PVT/CMF/MFI
which weight PRICE by volume or vice versa) strategy in this repo (0
prior hits on "Volume Weighted RSI"/"Volume RSI"/"VoRSI").

Signal logic
------------
- up_volume[t] = volume[t] if close[t] > close[t-1] else 0
- down_volume[t] = volume[t] if close[t] < close[t-1] else 0
- avg_up = SMA(up_volume, window); avg_down = SMA(down_volume, window)
- VoRS = avg_up / avg_down (guard against div-by-zero)
- VoRSI = 100 - 100 / (1 + VoRS)
- Entry (long): VoRSI crosses from at/below 50 to above 50.
- Exit: VoRSI crosses back below 50 (source's exact mirror rule),
  backstopped by a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _compute_vorsi(close: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    price_change = close.diff()
    up_volume = volume.where(price_change > 0, 0.0)
    down_volume = volume.where(price_change < 0, 0.0)

    avg_up = up_volume.rolling(window).mean()
    avg_down = down_volume.rolling(window).mean()

    # Guard against division by zero: where avg_down is 0 but avg_up > 0,
    # VoRSI should saturate at 100; where both are 0, treat as neutral (50).
    safe_down = avg_down.where(avg_down != 0, 1.0)
    vors = avg_up / safe_down
    vorsi = 100 - 100 / (1 + vors)
    vorsi = vorsi.where(avg_down != 0, 100.0)
    vorsi = vorsi.where(~((avg_down == 0) & (avg_up == 0)), 50.0)
    return vorsi.astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 14,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    vorsi = _compute_vorsi(close, volume, window)
    above_50 = vorsi > 50
    entry = above_50 & (~above_50.shift(1).fillna(False))
    exit_cross = ~above_50

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
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

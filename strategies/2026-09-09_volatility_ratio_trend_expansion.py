"""Strategy: Volatility Ratio (VR) trend-expansion filter, long-only.

Hypothesis (this iteration):
Per https://theindicatorlab.com/reviews/volatility-ratio/, the "Volatility
Ratio" indicator measures directional price movement relative to the
asset's own recent volatility: VR = |close - close.shift(vr_length)| /
ATR(vr_length), i.e. how many ATRs the price has moved over the lookback
window. VR expanding above a threshold signals a genuine directional move
(not noise); VR contracting signals chop/consolidation. This is distinct
from the already-tested Historical Volatility Ratio (2026-09-06-109,
ratio of two rolling STD-DEV windows, no directional/price-move
numerator) -- this VR's numerator is the actual net price displacement,
making it a volatility-NORMALIZED MOMENTUM oscillator rather than a pure
vol-of-vol ratio.

Per the source's own stated best-setup: "combining the ratio crossing
above 1.5 with the signal MA in an uptrend (price above the 200 EMA)
caught strong trends early without the usual false starts." Exit rule per
source: "Exit fully only when the ratio drops below 0.5" (a full-exit
threshold distinct from the entry threshold, i.e. an asymmetric
band/hysteresis exit rather than a simple crossunder of the entry level).

Signal logic
------------
- trend_window-period EMA trend filter: close > EMA(trend_window).
- VR = |close - close.shift(vr_length)| / ATR(vr_length).
- VR_signal = SMA(VR, signal_ma_window).
- Entry (long): VR crosses above entry_threshold (source default 1.5)
  AND VR > VR_signal AND close > EMA(trend_window).
- Exit: VR drops below exit_threshold (source default 0.5, a materially
  lower "full exit" band vs the entry threshold -- asymmetric hysteresis
  per source's own stated rule) OR close crosses below EMA(trend_window)
  (trend filter breaks) OR a max_hold_days time-stop backstop (source
  gives no explicit max-hold rule, but the loop's own convention of
  adding a backstop applies since VR can stay elevated indefinitely).

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

Sources:
    https://theindicatorlab.com/reviews/volatility-ratio/
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
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    vr_length: int = 20,
    signal_ma_window: int = 10,
    entry_threshold: float = 1.5,
    exit_threshold: float = 0.5,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    ema_trend = close.ewm(span=trend_window, adjust=False).mean()
    atr = _atr(df, vr_length)
    vr = (close - close.shift(vr_length)).abs() / atr.replace(0, np.nan)
    vr_signal = vr.rolling(signal_ma_window).mean()

    above_trend = close > ema_trend
    vr_cross_up_entry = (vr > entry_threshold) & (vr.shift(1) <= entry_threshold)
    entry_cond = (vr_cross_up_entry & (vr > vr_signal) & above_trend).fillna(False)
    exit_cond_static = ((vr < exit_threshold) | (~above_trend)).fillna(True)

    c = close.to_numpy(dtype=float)
    entry_arr = entry_cond.to_numpy(dtype=bool)
    exit_arr = exit_cond_static.to_numpy(dtype=bool)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if exit_arr[i] or held >= max_hold_days:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if entry_arr[i]:
                in_position = True
                entry_idx = i
                position[i] = 1
            else:
                position[i] = 0

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret

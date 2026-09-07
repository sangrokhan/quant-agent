"""Strategy: Weis Wave Volume + 200-EMA trend filter (David Weis VSA wave-volume).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per David Weis's Weis Wave Volume (WWV, 1990s Volume Spread Analysis
technique), transcribed at
https://pineify.app/pine-script/indicators/weis-wave-volume : WWV
accumulates total traded volume during each directional price "wave"
(a wave = a run of consecutive bars closing in the same direction relative
to the prior close), resetting to zero whenever the direction flips --
unlike cumulative volume indicators (OBV) it measures buying/selling
pressure PER WAVE, not running total. The source page's "Strategy 3 (Wave
Volume + EMA Trend Filter)" rule: only trust accumulation signals (an
up-wave with volume growing vs. the prior up-wave) when price is above a
200-period EMA (bull regime), entering long when that pattern appears;
exit when a distribution (down-wave with volume exceeding the prior
up-wave) pattern emerges or price closes back below the EMA200.

This is the first Weis Wave Volume strategy in this repo -- distinct from
OBV (cumulative, never resets), Klinger Volume Oscillator (EMA-difference
of an H/L/C-trend-weighted volume-force term), and VPCI/PVO (both EMA/SMA
ratio or difference constructions) since WWV is wave-segmented (volume
sums reset at each directional flip) rather than any smoothed/cumulative
running series.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  (0/1 long/flat)
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


def _weis_wave_volume(close: pd.Series, volume: pd.Series):
    """Return (wave_volume, wave_direction) series: wave_volume is the
    running accumulated volume within the CURRENT directional wave (resets
    to the bar's own volume when direction flips vs. the previous bar),
    wave_direction is +1/-1/0 (0 only possible on the very first bar).
    """
    n = len(close)
    direction = np.zeros(n, dtype=int)
    wave_vol = np.zeros(n, dtype=float)
    close_vals = close.to_numpy()
    vol_vals = volume.to_numpy()

    prev_dir = 0
    for i in range(n):
        if i == 0:
            direction[i] = 0
            wave_vol[i] = vol_vals[i]
            prev_dir = 0
            continue
        if close_vals[i] > close_vals[i - 1]:
            cur_dir = 1
        elif close_vals[i] < close_vals[i - 1]:
            cur_dir = -1
        else:
            cur_dir = prev_dir  # unchanged close: continue current wave
        if cur_dir != prev_dir and cur_dir != 0:
            wave_vol[i] = vol_vals[i]
        else:
            wave_vol[i] = wave_vol[i - 1] + vol_vals[i]
        direction[i] = cur_dir
        prev_dir = cur_dir

    return (
        pd.Series(wave_vol, index=close.index),
        pd.Series(direction, index=close.index),
    )


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 200,
    lookback_waves: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    wave_vol, wave_dir = _weis_wave_volume(close, volume)
    ema200 = close.ewm(span=ema_window, adjust=False).mean()
    bull_regime = close > ema200

    # A "completed" wave's total volume: the value of wave_vol on the LAST
    # bar of that wave (i.e. just before direction flips). We approximate
    # this at each bar by looking at the wave_vol value one bar before the
    # most recent flip for the prior up-wave / down-wave, using a simple
    # forward-fill of each wave's final tally captured at flip points.
    dir_shift = wave_dir.shift(1).fillna(0)
    is_flip = (wave_dir != dir_shift) & (dir_shift != 0)
    completed_wave_vol = wave_vol.shift(1).where(is_flip)
    completed_wave_dir = dir_shift.where(is_flip)

    last_up_vol = completed_wave_vol.where(completed_wave_dir == 1).ffill()
    last_down_vol = completed_wave_vol.where(completed_wave_dir == -1).ffill()
    prev_up_vol = last_up_vol.shift(1)
    prev_down_vol = last_down_vol.shift(1)

    # Accumulation signal: current up-wave's running volume already exceeds
    # the PRIOR completed up-wave's total volume, while still in an up-wave.
    accumulation = (wave_dir == 1) & (wave_vol > prev_up_vol.ffill())
    # Distribution signal: current down-wave's running volume exceeds the
    # prior completed up-wave's volume (selling overwhelming last buying wave).
    distribution = (wave_dir == -1) & (wave_vol > last_up_vol.ffill())

    entry = accumulation & bull_regime
    exit_signal = distribution | (~bull_regime)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret

"""Strategy: Weis Wave Volume "Low-Volume Wave Exhaustion" contrarian reversal.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://howtotrade.blog/what-is-weis-wave-volume-indicator/ (David Weis's
Weis Wave Volume, VSA/Wyckoff technique), the source distinguishes two
reversal setups: "High-Volume Wave Rejection" (huge volume, little price
progress) and "Low-Volume Wave Exhaustion" -- "diminishing wave heights
(step-down pattern) while price makes a marginal new high or new low ...
Lack of market interest. The current trend is running out of active
participants, causing the price to drift without backing." This is a
DIFFERENT, contrarian signal from this repo's existing WWV strategy
(strategies/2026-09-08_weis_wave_volume_ema_trend.py, which trades
trend-following ACCUMULATION: rising wave volume + EMA200 trend gate).
Here we test the opposite mechanic: after a down-wave that makes a marginal
new swing low on SHRINKING wave volume relative to the trailing average of
completed down-waves (sellers exhausted), go long anticipating a mean-revert
bounce, exiting on a fixed time-stop or a close back above the recent swing
high.

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
    """Return (wave_volume, wave_direction): wave_volume is the running
    accumulated volume within the CURRENT directional wave (resets to the
    bar's own volume when direction flips vs. the previous bar);
    wave_direction is +1/-1/0.
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
            cur_dir = prev_dir
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
    lookback_waves: int = 3,
    exhaustion_ratio: float = 0.6,
    new_low_window: int = 10,
    max_hold_days: int = 10,
    trend_window: int = 200,
    require_uptrend: bool = False,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    lookback_waves: number of prior COMPLETED down-waves averaged to form
        the "trailing average down-wave volume" baseline.
    exhaustion_ratio: a completed down-wave's own volume must be <= this
        fraction of the trailing average to count as "diminishing" /
        exhausted.
    new_low_window: the down-wave's low must be a marginal new low over
        this many trailing bars (source: "price makes a marginal new low").
    max_hold_days: time-stop exit.
    trend_window: optional SMA trend filter window.
    require_uptrend: if True, only take the reversal long when close is
        already above SMA(trend_window) (buy-the-dip variant); if False
        (default) the strategy is a pure contrarian bottom-fish with no
        trend gate, matching the source's own framing of exhaustion as a
        standalone reversal signal.
    """
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    volume = df["volume"]

    wave_vol, wave_dir = _weis_wave_volume(close, volume)

    dir_shift = wave_dir.shift(1).fillna(0)
    is_flip = (wave_dir != dir_shift) & (dir_shift != 0)
    completed_wave_vol = wave_vol.shift(1).where(is_flip)
    completed_wave_dir = dir_shift.where(is_flip)

    down_wave_vol_at_flip = completed_wave_vol.where(completed_wave_dir == -1)
    # Trailing average of the last `lookback_waves` completed down-waves,
    # evaluated only at flip points then forward-filled.
    down_avg_at_flip = (
        down_wave_vol_at_flip.dropna()
        .rolling(lookback_waves, min_periods=lookback_waves)
        .mean()
    )
    down_avg_at_flip = down_avg_at_flip.reindex(down_wave_vol_at_flip.index)
    trailing_down_avg = down_avg_at_flip.ffill().shift(1)  # avg of waves BEFORE this one

    rolling_low = low.rolling(new_low_window, min_periods=new_low_window).min()
    marginal_new_low = low <= rolling_low

    exhaustion_flip = (
        is_flip
        & (completed_wave_dir == -1)
        & (down_wave_vol_at_flip <= exhaustion_ratio * trailing_down_avg)
        & marginal_new_low.shift(1).fillna(False)
    )

    sma_trend = close.rolling(trend_window, min_periods=trend_window).mean()
    uptrend_ok = (close > sma_trend) if require_uptrend else pd.Series(True, index=close.index)

    swing_high = close.rolling(new_low_window, min_periods=new_low_window).max()
    exit_signal = close >= swing_high.shift(1)

    entry = exhaustion_flip & uptrend_ok

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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

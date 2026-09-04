"""Strategy: N-day high resistance breakout confirmed by relative-volume (RVOL) spike.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-166):
A close breaking above a rolling N-day high (resistance breakout) is a
higher-conviction long entry when confirmed by an above-average-volume
spike at the breakout bar (relative volume, RVOL = volume / rolling
average volume, >= a threshold e.g. 1.5x), signalling genuine institutional
participation rather than a low-conviction/likely-false breakout. Per
widely-corroborated volume-analysis rule snippets (Nydar's "Buy when price
breaks resistance on 50%+ above-average volume" == RVOL>=1.5x; onetradejournal's
RVOL bucket table: 1.0-1.5x weak, 1.5-2.0x+ stronger breakout signal). Exit
when price closes back below a shorter-term trailing low (Donchian-style
exit distinct from the entry lookback) or a max_hold_days time-stop. First
strategy in this repo to gate a pure price-level breakout with a
volume-SPIKE (RVOL ratio) confirmation filter rather than a volume-momentum
oscillator (OBV/CMF/AD-line/Force-Index, all already tested) or a plain
trend-SMA filter.

Signal logic
------------
- Breakout level = rolling_max(high, breakout_window).shift(1) (prior N-day
  high, excludes current bar to avoid look-ahead).
- RVOL = volume / rolling_mean(volume, vol_window).
- Entry (long): close crosses above the breakout level AND RVOL >=
  rvol_threshold at that bar.
- Exit level = rolling_min(low, exit_window).shift(1) (prior M-day low).
- Exit: close crosses below the exit level, OR max_hold_days elapses.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
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


def generate_signals(
    price_df: pd.DataFrame,
    breakout_window: int = 20,
    exit_window: int = 10,
    vol_window: int = 20,
    rvol_threshold: float = 1.5,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)

    breakout_level = high.rolling(breakout_window).max().shift(1)
    exit_level = low.rolling(exit_window).min().shift(1)
    avg_vol = volume.rolling(vol_window).mean()
    rvol = (volume / avg_vol.replace(0.0, np.nan)).fillna(0.0)

    cross_above_breakout = (close > breakout_level) & (close.shift(1) <= breakout_level.shift(1))
    cross_below_exit = (close < exit_level) & (close.shift(1) >= exit_level.shift(1))

    entry_raw = cross_above_breakout & (rvol >= rvol_threshold)
    exit_raw = cross_below_exit

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_days = 0
    entry_arr = entry_raw.fillna(False).to_numpy()
    exit_arr = exit_raw.fillna(False).to_numpy()
    pos_arr = position.to_numpy().copy()

    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            if exit_arr[i] or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    position = pd.Series(pos_arr, index=df.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    breakout_window: int = 20,
    exit_window: int = 10,
    vol_window: int = 20,
    rvol_threshold: float = 1.5,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        breakout_window=breakout_window,
        exit_window=exit_window,
        vol_window=vol_window,
        rvol_threshold=rvol_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

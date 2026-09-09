"""Strategy: Wyckoff Spring (volume-confirmed) -- direct follow-up to this
cron trigger's own near-miss/rejected plain Spring (2026-09-09-105,
decisive Sharpe+MDD fail, 0.049 grid pass_fraction).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per algobars.com's Wyckoff Spring rule set (full dedicated strategy
template page): "Volume on the spring is LOW (no real selling)... The key
to identifying a Spring vs a genuine breakdown is volume. A true Spring
occurs on diminishing volume." This is EXACTLY the confirmation filter
flagged as missing in the plain-Spring rejection's `notes` field
(2026-09-09-105: "the source explicitly notes volume/spread confirmation
matters -- a future revisit could add a low-volume-on-probe filter").

Adds one gate on top of the identical probe/reclaim mechanism: the probe
bar's volume must be BELOW its own trailing average volume (vol_ma_window
lookback) by at least vol_ratio_max (e.g. <=0.8x average = "diminishing
volume", per algobars' own stated rule), confirming genuine accumulation
rather than a real breakdown. Same exit logic (range-high target,
probe-low stop, max_hold_days time-stop) as the parent strategy, so any
change in outcome is attributable to the volume filter alone.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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
    range_window: int = 20,
    confirm_bars: int = 1,
    vol_ma_window: int = 20,
    vol_ratio_max: float = 0.8,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    high = df["high"]
    volume = df["volume"] if "volume" in df.columns else None

    range_low = low.shift(1).rolling(range_window).min()
    range_high = high.shift(1).rolling(range_window).max()

    probe_below = low < range_low

    if volume is not None:
        vol_avg = volume.rolling(vol_ma_window).mean()
        low_volume_probe = volume <= (vol_avg * vol_ratio_max)
        probe_below = probe_below & low_volume_probe

    if confirm_bars <= 1:
        spring_confirmed = probe_below & (close > range_low)
    else:
        close_back_inside = close > range_low
        confirmed_recent = close_back_inside.rolling(confirm_bars, min_periods=1).max().astype(bool)
        spring_confirmed = probe_below.shift(confirm_bars - 1).fillna(False).astype(bool) & confirmed_recent

    probe_low_value = low.where(probe_below).ffill()

    idx_list = close.index
    entry_arr = spring_confirmed.reindex(idx_list).fillna(False).to_numpy()
    close_arr = close.to_numpy()
    range_high_arr = range_high.to_numpy()
    probe_low_arr = probe_low_value.reindex(idx_list).to_numpy()

    pos_arr = [0] * len(idx_list)
    in_position = False
    entry_idx = -1
    stop_level = None

    for i in range(len(idx_list)):
        if not in_position:
            if entry_arr[i]:
                in_position = True
                entry_idx = i
                stop_level = probe_low_arr[i]
                pos_arr[i] = 1
        else:
            held = i - entry_idx
            hit_target = (range_high_arr[i] == range_high_arr[i]) and close_arr[i] > range_high_arr[i]
            hit_stop = (stop_level == stop_level) and close_arr[i] < stop_level
            if hit_target or hit_stop or held >= max_hold_days:
                in_position = False
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1

    return pd.Series(pos_arr, index=idx_list, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    range_window: int = 20,
    confirm_bars: int = 1,
    vol_ma_window: int = 20,
    vol_ratio_max: float = 0.8,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        range_window=range_window,
        confirm_bars=confirm_bars,
        vol_ma_window=vol_ma_window,
        vol_ratio_max=vol_ratio_max,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret

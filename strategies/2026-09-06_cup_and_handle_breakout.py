"""Strategy: Cup-and-Handle breakout (William O'Neil / CANSLIM specification).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per this iteration's research (tradiecapital.com's detailed spec, sourced
from William O'Neil's CANSLIM methodology), the cup-and-handle is a
bullish continuation pattern: a stock in an existing uptrend corrects
12-33% in a rounded U-shape over 7-65 weeks (the "cup"), rallies back
near its prior high, then drifts down mildly for 1-4 weeks on contracting
volume in the UPPER HALF of the cup (the "handle" -- a final shakeout of
weak holders). The buy signal triggers on a breakout above the handle's
high with volume at least 40% above its recent average; a protective
stop sits below the handle's low. First cup-and-handle strategy in this
repo -- distinct from all V-shaped/single-swing reversal patterns
(Tweezer Bottom, Bullish Harami, Morning Star, etc.) via its specific
two-stage rounded-correction-then-shakeout structure and explicit
volume-contraction/volume-surge requirements.

Signal logic (mechanical operationalization of the source's spec)
-------------------------------------------------------------------
Scanning a rolling window of `cup_lookback_days` (default ~130 trading
days, mid-point of the source's 7-65 week range), for each bar t:
  1. Left rim: the window's max close, at index `peak_idx`.
  2. Cup bottom: the min close AFTER peak_idx within the window, at
     `trough_idx`. Cup depth = (peak - trough) / peak. Must be within
     [min_cup_depth_pct, max_cup_depth_pct] (source: 12-33%).
  3. Cup must be "U" not "V": require the cup to span at least
     `min_cup_days` trading days (source: 7 weeks ~= 35 days) between
     peak_idx and trough_idx combined with the current bar.
  4. Recovery: price must have climbed back within `near_high_pct` of
     the left-rim peak (source: near the old high) sometime after
     trough_idx and before the handle begins.
  5. Handle: after the recovery high (`handle_start_idx`), price drifts
     down for `handle_min_days`-`handle_max_days` (source: 1-4 weeks ~=
     5-20 days), staying above the cup's midpoint (peak+trough)/2 (source:
     "upper half of the cup"), with average volume over the handle below
     `handle_vol_contraction_ratio` times the cup's own average volume
     (source: "contracting volume").
  6. Breakout entry: close breaks above the handle's own high AND
     volume >= `volume_surge_mult` x the 20-day average volume (source:
     "40 to 50% above average" -> volume_surge_mult=1.4 default).
  7. Exit: close below the handle's low (stop, source's own rule), OR
     close reaches the measured-move target (breakout_price + cup_depth
     in price terms), OR a max_hold_days time-stop.

This is inherently a rarer, more selective signal than most strategies in
this repo (multi-week structural pattern, not a single-bar indicator
condition) -- expect fewer trades.

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


def _detect_cup_handle_breakout(
    close: pd.Series,
    volume: pd.Series,
    cup_lookback_days: int,
    min_cup_depth_pct: float,
    max_cup_depth_pct: float,
    min_cup_days: int,
    near_high_pct: float,
    handle_min_days: int,
    handle_max_days: int,
    handle_vol_contraction_ratio: float,
    volume_surge_mult: float,
) -> pd.Series:
    """Returns a boolean Series: True on bars where a valid cup-and-handle
    breakout fires. Also returns (via closure state) the handle low/high
    and measured-move target for that breakout, needed by generate_signals
    for exit logic -- packed into a parallel dict keyed by breakout index.
    """
    n = len(close)
    breakout = pd.Series(False, index=close.index)
    breakout_info: dict = {}
    vol_avg20 = volume.rolling(20).mean()

    for t in range(cup_lookback_days, n):
        window_close = close.iloc[t - cup_lookback_days:t]
        peak_pos = window_close.values.argmax()
        peak_val = window_close.iloc[peak_pos]
        after_peak = window_close.iloc[peak_pos:]
        if len(after_peak) < min_cup_days:
            continue
        trough_pos_local = after_peak.values.argmin()
        trough_val = after_peak.iloc[trough_pos_local]
        cup_depth_pct = (peak_val - trough_val) / peak_val if peak_val > 0 else 0
        if not (min_cup_depth_pct <= cup_depth_pct <= max_cup_depth_pct):
            continue
        cup_span_days = trough_pos_local  # from peak to trough
        if cup_span_days < min_cup_days // 2:
            continue

        # after trough: look for recovery near old high, then a handle,
        # then check if `t` itself is the breakout bar.
        post_trough = after_peak.iloc[trough_pos_local:]
        recovery_mask = post_trough >= peak_val * (1 - near_high_pct)
        if not recovery_mask.any():
            continue
        recovery_local_pos = recovery_mask.values.argmax()
        if recovery_local_pos == 0:
            continue

        handle_start = post_trough.iloc[recovery_local_pos:]
        handle_len = len(handle_start) - 1  # bars after the recovery high, up to (not incl) t
        if not (handle_min_days <= handle_len <= handle_max_days):
            continue

        handle_series = handle_start  # includes recovery high bar through bar t
        if len(handle_series) < 2:
            continue
        handle_high = handle_series.iloc[:-1].max()  # exclude current bar t
        handle_low = handle_series.iloc[:-1].min()
        cup_mid = (peak_val + trough_val) / 2.0
        if handle_low < cup_mid:
            continue  # handle must stay in upper half of cup

        # volume contraction check
        cup_vol_avg = volume.iloc[t - cup_lookback_days:t].mean()
        handle_start_abs = t - handle_len
        handle_vol_avg = volume.iloc[handle_start_abs:t].mean()
        if cup_vol_avg <= 0 or handle_vol_avg > handle_vol_contraction_ratio * cup_vol_avg:
            continue

        # breakout check at bar t
        current_close = close.iloc[t]
        current_vol = volume.iloc[t]
        avg20 = vol_avg20.iloc[t]
        if pd.isna(avg20) or avg20 <= 0:
            continue
        if current_close > handle_high and current_vol >= volume_surge_mult * avg20:
            breakout.iloc[t] = True
            breakout_info[t] = {
                "handle_low": float(handle_low),
                "cup_depth_price": float(peak_val - trough_val),
                "breakout_price": float(current_close),
            }

    return breakout, breakout_info


def generate_signals(
    price_df: pd.DataFrame,
    cup_lookback_days: int = 130,
    min_cup_depth_pct: float = 0.12,
    max_cup_depth_pct: float = 0.33,
    min_cup_days: int = 35,
    near_high_pct: float = 0.05,
    handle_min_days: int = 5,
    handle_max_days: int = 20,
    handle_vol_contraction_ratio: float = 0.8,
    volume_surge_mult: float = 1.4,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    breakout, breakout_info = _detect_cup_handle_breakout(
        close, volume, cup_lookback_days, min_cup_depth_pct, max_cup_depth_pct,
        min_cup_days, near_high_pct, handle_min_days, handle_max_days,
        handle_vol_contraction_ratio, volume_surge_mult,
    )

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = None
    target_price = None

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            c = close.iloc[i]
            if c < stop_price or c >= target_price or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(breakout.iloc[i]):
                info = breakout_info[i]
                in_position = True
                entry_idx = i
                stop_price = info["handle_low"]
                target_price = info["breakout_price"] + info["cup_depth_price"]
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    cup_lookback_days: int = 130,
    min_cup_depth_pct: float = 0.12,
    max_cup_depth_pct: float = 0.33,
    min_cup_days: int = 35,
    near_high_pct: float = 0.05,
    handle_min_days: int = 5,
    handle_max_days: int = 20,
    handle_vol_contraction_ratio: float = 0.8,
    volume_surge_mult: float = 1.4,
    max_hold_days: int = 40,
) -> pd.Series:
    """Daily strategy returns: position (lagged by 1 bar to avoid
    lookahead) times the underlying daily simple return."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        cup_lookback_days=cup_lookback_days,
        min_cup_depth_pct=min_cup_depth_pct,
        max_cup_depth_pct=max_cup_depth_pct,
        min_cup_days=min_cup_days,
        near_high_pct=near_high_pct,
        handle_min_days=handle_min_days,
        handle_max_days=handle_max_days,
        handle_vol_contraction_ratio=handle_vol_contraction_ratio,
        volume_surge_mult=volume_surge_mult,
        max_hold_days=max_hold_days,
    )
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_returns

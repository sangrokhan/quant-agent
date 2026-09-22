"""Strategy: Crypto ORB v2 -- ATR-range-filtered + RVOL-confirmed opening range
breakout (rescue attempt on 2026-09-04-148).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: https://tradersentiments.com/trading-strategies/opening-range-breakout
(accessed 2026-09-22). The article's "Essential Indicator Confirmation
Stack" gives two concrete, numeric filters that the repo's prior
first-generation crypto ORB (id 2026-09-04-148, rejected: 71%/53% max
drawdown, deeply negative net Sharpe after costs, decisively too noisy) did
NOT use, and which that entry's own `notes` flagged as the specific rescue
idea worth trying:
  1. **Range-size filter**: only take the trade if the opening range height
     (OR_high - OR_low) falls between `atr_range_min` and `atr_range_max`
     fraction of a rolling ATR (skip days where the range is already too
     wide -- "directional move exhausted" -- or too narrow to be
     meaningful).
  2. **Relative-volume (RVOL) confirmation**: only take the breakout if the
     opening-range period's volume exceeds `rvol_threshold`x its own
     rolling same-hour-of-day average volume (source recommends RVOL > 1.5),
     as a proxy for "real institutional participation" rather than noise.
The source's exit management (scale out at 1R, trail the runner behind a
short EMA) is approximated here with a single EMA trailing-stop exit
(`trail_ema_span`) plus a max-hold time-stop, keeping the interface simple.

Since data/loaders.py's equity path is daily-bar-only (no true opening
range on equities, as already established in 2026-09-04-148's notes), this
remains deliberately CRYPTO-ONLY on 1h bars, same honest scoping as the
strategy being rescued.

Signal logic (crypto, 1h bars, per UTC calendar day)
-----------------------------------------------------
- Opening range = first `range_hours` 1h bars of each UTC day
  (OR_high/OR_low = max high / min low over that window).
- ATR(atr_window) computed on 1h bars (a rolling volatility proxy, not a
  true daily ATR, given the bar granularity available).
- RVOL = opening-range total volume / rolling mean of opening-range-window
  volume over the trailing `rvol_lookback_days` days (same hour-of-day
  alignment via UTC day grouping).
- Entry (long), evaluated once per day right after the opening range closes:
    - (OR_high - OR_low) / ATR is within [atr_range_min, atr_range_max]
    - RVOL >= rvol_threshold
    - a later same-day bar closes above OR_high
- Exit: close crosses below a trailing EMA(trail_ema_span) computed on
  close (approximates "trail behind the 9 EMA"), OR close drops back below
  OR_low (failed breakout), OR UTC day rolls over (flat overnight, same as
  the strategy being rescued), OR max_hold_hours elapsed.
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
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    range_hours: int = 4,
    atr_window: int = 480,  # ~20 days of 1h bars
    atr_range_min: float = 0.25,
    atr_range_max: float = 0.60,
    rvol_lookback_days: int = 20,
    rvol_threshold: float = 1.5,
    trail_ema_span: int = 9,
    max_hold_hours: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    day = df.index.normalize()
    df = df.assign(_day=day)

    atr = _atr(df, atr_window)

    ema = df["close"].ewm(span=trail_ema_span, adjust=False).mean()

    grp = df.groupby("_day")
    or_high_by_day = {}
    or_low_by_day = {}
    or_vol_by_day = {}
    for d, g in grp:
        window = g.iloc[:range_hours]
        or_high_by_day[d] = window["high"].max()
        or_low_by_day[d] = window["low"].min()
        or_vol_by_day[d] = window["volume"].sum() if "volume" in window.columns else np.nan

    or_high_series = pd.Series(or_high_by_day).sort_index()
    or_low_series = pd.Series(or_low_by_day).sort_index()
    or_vol_series = pd.Series(or_vol_by_day).sort_index()
    or_vol_avg = or_vol_series.rolling(rvol_lookback_days, min_periods=5).mean().shift(1)
    rvol_series = or_vol_series / or_vol_avg

    day_or_high = df["_day"].map(or_high_series)
    day_or_low = df["_day"].map(or_low_series)
    day_rvol = df["_day"].map(rvol_series)

    # ATR at the end of the opening range window (approx: ATR value at the
    # range_hours-th bar of each day), broadcast to the whole day.
    atr_at_or_end = {}
    for d, g in grp:
        if len(g) >= range_hours:
            atr_at_or_end[d] = atr.loc[g.index[range_hours - 1]]
        else:
            atr_at_or_end[d] = np.nan
    atr_or_series = pd.Series(atr_at_or_end).sort_index()
    day_atr = df["_day"].map(atr_or_series)

    or_size = day_or_high - day_or_low
    range_ratio = or_size / day_atr

    range_ok = (range_ratio >= atr_range_min) & (range_ratio <= atr_range_max)
    rvol_ok = day_rvol >= rvol_threshold
    day_gate = (range_ok & rvol_ok).fillna(False)

    close = df["close"]
    # Identify bars that are part of the opening range window itself (skip
    # trading during range formation).
    or_bar_flags = pd.Series(False, index=df.index)
    for d, g in grp:
        or_bar_flags.loc[g.index[:range_hours]] = True

    entry_trigger = (close > day_or_high) & (~or_bar_flags) & day_gate
    exit_trail = close < ema
    exit_or_low = close < day_or_low
    exit_trigger = exit_trail | exit_or_low

    pos_arr = [0] * len(df)
    in_pos = False
    hold_hours = 0
    cur_day = None
    entry_arr = entry_trigger.fillna(False).to_numpy()
    exit_arr = exit_trigger.fillna(True).to_numpy()
    day_arr = df["_day"].to_numpy()

    for i in range(len(df)):
        if in_pos and day_arr[i] != cur_day:
            in_pos = False
            hold_hours = 0

        if in_pos:
            hold_hours += 1
            if exit_arr[i] or hold_hours >= max_hold_hours:
                in_pos = False
                hold_hours = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_hours = 0
                cur_day = day_arr[i]
                pos_arr[i] = 1

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    range_hours: int = 4,
    atr_window: int = 480,
    atr_range_min: float = 0.25,
    atr_range_max: float = 0.60,
    rvol_lookback_days: int = 20,
    rvol_threshold: float = 1.5,
    trail_ema_span: int = 9,
    max_hold_hours: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        range_hours=range_hours,
        atr_window=atr_window,
        atr_range_min=atr_range_min,
        atr_range_max=atr_range_max,
        rvol_lookback_days=rvol_lookback_days,
        rvol_threshold=rvol_threshold,
        trail_ema_span=trail_ema_span,
        max_hold_hours=max_hold_hours,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

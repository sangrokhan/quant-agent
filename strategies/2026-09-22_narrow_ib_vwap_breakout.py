"""Strategy: Narrow Initial-Balance (IB) breakout, VWAP-trend confirmed.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: https://algobars.com/strategy-templates/market-profile/ib-breakout/
(accessed 2026-09-22, browser_exec after web_extract refused ddgs-backend
extraction). The page's "Initial Balance Breakout" Market-Profile template
gives concrete numeric rules distinct from this repo's existing crypto ORB
strategies (2026-09-04-148 rejected plain ORB; 2026-09-22-XXX ATR-range +
RVOL rescue):
  1. IB = the range formed in the first `ib_hours` hours of each trading day.
  2. Only trade IB days where the IB range is NARROW relative to its own
     recent history -- source's own "Pro Tip": "the narrowest IB days
     (bottom 20% of 20-day average) produce the strongest Trend Days."
     Implemented here as an IB-range PERCENTILE RANK filter
     (`ib_narrow_pct`, default bottom 20th percentile of the trailing
     `ib_lookback_days` days), rather than the ATR-ratio-band filter the
     prior rescue attempt used -- a different (percentile-of-own-history)
     narrowness mechanic.
  3. Entry (long): a later same-day bar closes above the IB high, AND VWAP
     (source's stated confirmation indicator) is trending upward (VWAP
     itself is rising over `vwap_slope_lookback` bars) -- source: "VWAP must
     be trending upward."
  4. Target: source states "Target: 1.5x IB range from breakout" -- a fixed
     take-profit expressed as a multiple of the IB range added to the
     breakout price, implemented here as `ib_target_mult`.
  5. Stop / other exit: source doesn't give a numeric stop; conservatively
     add a same-day close-below-IB-low failed-breakout stop and end-of-day
     flatten (consistent with this repo's other single-day-hold ORB
     strategies), plus a `max_hold_hours` time-stop.

This is deliberately CRYPTO-ONLY (1h bars) since data/loaders.py's equity
path is daily-bar-only and has no true opening-range/IB concept (same
established constraint noted in 2026-09-04-148 and the ATR/RVOL rescue).

Signal logic (crypto, 1h bars, per UTC calendar day)
-----------------------------------------------------
- IB = first `ib_hours` 1h bars of each UTC day; IB_high/IB_low = max
  high / min low over that window; ib_size = IB_high - IB_low.
- Anchored VWAP recomputed each UTC day from the day's own bars (cumulative
  typical-price-volume / cumulative volume), a per-day session VWAP as is
  standard for Market Profile-style day-session analysis.
- ib_size_pctrank = rolling percentile rank of today's ib_size among the
  trailing `ib_lookback_days` days' ib_size values (0 = narrowest, 1 =
  widest). Day gate: ib_size_pctrank <= ib_narrow_pct.
- VWAP slope filter: VWAP value `vwap_slope_lookback` bars ago vs current
  VWAP value; require current > past (upward trend).
- Entry (long), evaluated on bars after the IB window closes:
    - close > IB_high (breakout)
    - ib_size_pctrank <= ib_narrow_pct (narrow-IB day gate)
    - VWAP rising over vwap_slope_lookback bars
- Exit: close >= IB_high + ib_target_mult * ib_size (target hit), OR
  close < IB_low (failed-breakout stop), OR UTC day rolls over (flatten
  overnight), OR max_hold_hours elapsed.
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


def _session_vwap(df: pd.DataFrame, day: pd.Series) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    vol = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)
    pv = typical * vol
    cum_pv = pv.groupby(day).cumsum()
    cum_v = vol.groupby(day).cumsum().replace(0, np.nan)
    return cum_pv / cum_v


def generate_signals(
    price_df: pd.DataFrame,
    ib_hours: int = 4,
    ib_lookback_days: int = 20,
    ib_narrow_pct: float = 0.20,
    vwap_slope_lookback: int = 3,
    ib_target_mult: float = 1.5,
    max_hold_hours: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    day = df.index.normalize()
    df = df.assign(_day=day)

    vwap = _session_vwap(df, df["_day"])

    grp = df.groupby("_day")
    ib_high_by_day = {}
    ib_low_by_day = {}
    for d, g in grp:
        window = g.iloc[:ib_hours]
        ib_high_by_day[d] = window["high"].max()
        ib_low_by_day[d] = window["low"].min()

    ib_high_series = pd.Series(ib_high_by_day).sort_index()
    ib_low_series = pd.Series(ib_low_by_day).sort_index()
    ib_size_series = ib_high_series - ib_low_series

    # Rolling percentile rank of today's IB size vs trailing history
    # (strictly using PRIOR days -- shift(1) window -- to avoid lookahead,
    # then compare today's value against that prior distribution).
    def _pctrank_today(s: pd.Series, lookback: int) -> pd.Series:
        out = pd.Series(index=s.index, dtype=float)
        vals = s.to_numpy()
        for i in range(len(s)):
            lo = max(0, i - lookback)
            hist = vals[lo:i]  # prior days only
            if len(hist) < 5 or np.isnan(vals[i]):
                out.iloc[i] = np.nan
            else:
                out.iloc[i] = float((hist <= vals[i]).sum()) / len(hist)
        return out

    ib_pctrank_series = _pctrank_today(ib_size_series, ib_lookback_days)

    day_ib_high = df["_day"].map(ib_high_series)
    day_ib_low = df["_day"].map(ib_low_series)
    day_ib_size = df["_day"].map(ib_size_series)
    day_ib_pctrank = df["_day"].map(ib_pctrank_series)

    narrow_gate = (day_ib_pctrank <= ib_narrow_pct).fillna(False)

    vwap_past = vwap.shift(vwap_slope_lookback)
    vwap_rising = (vwap > vwap_past).fillna(False)

    close = df["close"]
    or_bar_flags = pd.Series(False, index=df.index)
    for d, g in grp:
        or_bar_flags.loc[g.index[:ib_hours]] = True

    entry_trigger = (close > day_ib_high) & (~or_bar_flags) & narrow_gate & vwap_rising
    target_price = day_ib_high + ib_target_mult * day_ib_size
    exit_target = close >= target_price
    exit_stop = close < day_ib_low
    exit_trigger = exit_target | exit_stop

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
    ib_hours: int = 4,
    ib_lookback_days: int = 20,
    ib_narrow_pct: float = 0.20,
    vwap_slope_lookback: int = 3,
    ib_target_mult: float = 1.5,
    max_hold_hours: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        ib_hours=ib_hours,
        ib_lookback_days=ib_lookback_days,
        ib_narrow_pct=ib_narrow_pct,
        vwap_slope_lookback=vwap_slope_lookback,
        ib_target_mult=ib_target_mult,
        max_hold_hours=max_hold_hours,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

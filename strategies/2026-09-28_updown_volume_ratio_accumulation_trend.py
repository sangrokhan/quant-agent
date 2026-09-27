"""Strategy: Up/down Volume Ratio accumulation-confirmed trend-following long.

Hypothesis (source: https://www.luxalgo.com/library/indicator/up-down-volume-ratio/,
read 2026-09-28 via browser_exec direct navigation -- web_search for "less
common LuxAlgo volume indicators" surfaced only the library's family-listing
page, not this specific indicator's detail page, so browser_exec was used to
open it directly):

LuxAlgo's Up/down Volume Ratio sums the volume traded on advancing bars,
divides it by the volume traded on declining bars, over a rolling window
(source default: 50 bars), and reads the result against a fixed 1.0 balance
level: above 1.0 means accumulated volume favors advancing bars (net
accumulation); below 1.0 means net distribution. Source's own trading
guidance: "Level plus trend: the optional Ratio Trend line adds direction.
Above 1.0 and rising is the classic accumulation signature."

This is a genuinely different construction from every prior volume-family
strategy in this repo: OBV/PVT are cumulative signed-volume LINES (no fixed
balance level), CMF/MFI are money-flow oscillators weighting volume by
price *position* within the bar range, and VoRSI (this repo's closest
relative, tested 2026-09-09-098 / 2026-09-14-188) applies the RSI SMOOTHING
formula to up/down volume rather than a raw ratio-of-sums against a fixed
1.0 threshold. Zero prior hits for "up/down volume ratio" or "up-down
volume" in strategies_index.jsonl.

Hypothesis: on a daily-bar SMA(trend_window) uptrend gate, requiring the
Up/down Volume Ratio to be ABOVE 1.0 AND RISING (per source's own "classic
accumulation signature" framing) confirms genuine volume-backed
participation behind an entry, filtering out weak/thin breakouts that a
plain SMA-cross would take blindly. Exit on ratio-trend deterioration below
1.0, trend-filter break, or a time-stop.

Signal logic (daily-bar mechanical proxy for source's rolling-window ratio):
- up_volume: bar's volume where close > close.shift(1) (source's
  "Previous Close" up/down basis, "Bar Direction" volume split -- the
  simplest of the source's several configurable variants).
- down_volume: bar's volume where close < close.shift(1).
- ratio = rolling_sum(up_volume, window) / rolling_sum(down_volume, window)
  (source's rolling accumulation-window default mode, vs. session-totals).
- ratio_trend = SMA(ratio, trend_len) (source's optional Trend Line,
  default type SMA, default length 10).
- Baseline trend gate: close > SMA(trend_window).
- Entry: trend gate true AND ratio > 1.0 AND ratio > ratio_trend (rising
  accumulation signature) AND not already in a position.
- Exit: trend gate breaks (close < SMA(trend_window)), OR ratio crosses
  back below 1.0 (net distribution), OR max_hold_days time-stop --
  whichever comes first.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _updown_volume_ratio(df: pd.DataFrame, window: int, trend_len: int) -> tuple[pd.Series, pd.Series]:
    close = df["close"]
    volume = df["volume"]
    prior_close = close.shift(1)

    up_vol = volume.where(close > prior_close, 0.0)
    down_vol = volume.where(close < prior_close, 0.0)

    up_sum = up_vol.rolling(window).sum()
    down_sum = down_vol.rolling(window).sum()

    # Avoid division by zero -- when down_sum is 0 but up_sum > 0, treat as
    # a very strong (but finite) accumulation reading rather than inf.
    ratio = up_sum / down_sum.replace(0.0, np.nan)
    ratio = ratio.ffill()
    ratio_trend = ratio.rolling(trend_len).mean()

    return ratio, ratio_trend


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    ratio_window: int = 50,
    ratio_trend_len: int = 10,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(trend_window).mean()
    trend_ok = close > sma

    ratio, ratio_trend = _updown_volume_ratio(df, ratio_window, ratio_trend_len)
    accumulation_ok = (ratio > 1.0) & (ratio > ratio_trend)
    distribution = ratio < 1.0

    n = len(df)
    trend_ok_arr = trend_ok.to_numpy()
    accumulation_ok_arr = accumulation_ok.fillna(False).to_numpy()
    distribution_arr = distribution.fillna(False).to_numpy()

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = (
                not bool(trend_ok_arr[i])
                or bool(distribution_arr[i])
                or hold_count >= max_hold_days
            )
            if exit_now:
                in_pos = False
                hold_count = 0
            else:
                pos.iloc[i] = 1.0
        if not in_pos and bool(trend_ok_arr[i]) and bool(accumulation_ok_arr[i]):
            in_pos = True
            hold_count = 0
            pos.iloc[i] = 1.0

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    ratio_window: int = 50,
    ratio_trend_len: int = 10,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        trend_window=trend_window,
        ratio_window=ratio_window,
        ratio_trend_len=ratio_trend_len,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret

"""Strategy: FRAMA (Fractal Adaptive Moving Average) ATR-band breakout,
long-only adaptation of John Ehlers' FRAMA trend-following system.

Hypothesis (source: https://oxfordstrat.com/trading-strategies/fractal-adaptive-moving-average/,
read 2026-09-28 via browser_exec, web_search's DDGS backend intermittently
returning empty/errored results this iteration for unrelated earlier
queries, extract done directly with browser since web_extract's ddgs
backend is search-only and cannot fetch page content):

Oxford Strat's disclosed specification for Ehlers' FRAMA trading strategy
(tested there on 42 futures markets, 1980-2016, MATLAB backtest) is fully
mechanical:
- FRAMA(Price, FRAMA_Length) is the Fractal Adaptive Moving Average of
  Price=(High+Low)/2 over a lookback FRAMA_Length. FRAMA adapts its own
  smoothing constant to the *fractal dimension* of price action -- it
  hugs price tightly in trending/low-fractal-dimension conditions and
  flattens out (acts like a slow SMA) in choppy/high-fractal-dimension
  conditions. Formula (Ehlers 2005, "FRAMA"): split the lookback window
  into two halves, compute each half's own (range/length) "N1"/"N2", the
  whole window's "N3", fractal dimension D=(log(N1+N2)-log(N3))/log(2),
  smoothing alpha=exp(-4.6*(D-1)) clipped to [alpha_min, 1], then
  FRAMA[t] = alpha*Price[t] + (1-alpha)*FRAMA[t-1].
- Source's own disclosed entry/exit bands:
    Entry_Upper_Band[i]  = FRAMA[i] + ATR_Band * ATR[i]
    Exit_Lower_Band[i]   = FRAMA[i] - 0.5 * ATR_Band * ATR[i]
  Long Trade Setup: Close[i-1] > Entry_Upper_Band[i-1] -> buy next bar.
  Trend Exit: Close[i-1] < Exit_Lower_Band[i-1] (note: source's Exit_Lower
  uses HALF the entry band width, i.e. exit tighter/sooner than the
  symmetric entry threshold -- source's own asymmetric design choice) ->
  sell next bar.
  Stop-Loss Exit: hard stop at Entry - ATR(ATR_Length)*ATR_Stop
  (source's own base case: ATR_Length=20 for the stop's own ATR calc,
  ATR_Stop=6 -- a wide catastrophic-only stop, not a tight trailing stop).
- Source's own benchmarking table (Table 2) varies ATR_Length in
  {60,80,100,120} at fixed ATR_Band=3 and reports Sharpe 0.71-0.81 with
  MDD 39-54% on a 42-future multi-asset trend-following portfolio --
  source's own summary explicitly states this strategy "does not perform
  significantly better than alternative [MA-filter] strategies" and that
  the underlying fractal-dimension approximation is "very inaccurate" --
  i.e. the source itself does NOT claim this is a strong edge, only a
  fully disclosed, testable mechanical baseline. Worth testing fresh on
  this repo's specific equity/crypto universe and single-symbol daily-bar
  scale (very different from the source's 42-future/1980-2016 multi-asset
  portfolio test) rather than assuming the source's own modest verdict
  transfers directly.

This repo is long-only (SAFETY.md) -- the short-trade leg of the source's
system is dropped; only the long Entry_Upper_Band breakout / Exit_Lower_Band
trend-exit / ATR hard-stop are implemented. First FRAMA-based strategy in
this repo (0 prior "Fractal Adaptive Moving Average"/"FRAMA" hits in
strategies_index.jsonl) -- distinct from all prior adaptive-smoothing
strategies already tested (Kaufman KAMA efficiency-ratio-driven smoothing,
Ehlers Adaptive Laguerre Filter, MAMA/FAMA Hilbert-transform-adaptive) since
FRAMA's adaptation mechanism is the fractal box-counting dimension of price
range over two half-windows, not an efficiency ratio or a Hilbert-transform
cycle period.

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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _frama(df: pd.DataFrame, frama_length: int, alpha_min: float = 0.01) -> pd.Series:
    """Ehlers' Fractal Adaptive Moving Average.

    frama_length must be even (split into two equal halves each period).
    """
    if frama_length % 2 != 0:
        frama_length += 1  # enforce even window, source's own convention

    half = frama_length // 2
    price = (df["high"] + df["low"]) / 2.0
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n = len(df)

    frama = np.full(n, np.nan)
    price_arr = price.to_numpy()

    for i in range(frama_length - 1, n):
        window_start = i - frama_length + 1
        mid = window_start + half

        h1 = np.max(high[window_start:mid])
        l1 = np.min(low[window_start:mid])
        n1 = (h1 - l1) / half

        h2 = np.max(high[mid : i + 1])
        l2 = np.min(low[mid : i + 1])
        n2 = (h2 - l2) / half

        h3 = np.max(high[window_start : i + 1])
        l3 = np.min(low[window_start : i + 1])
        n3 = (h3 - l3) / frama_length

        if n1 > 0 and n2 > 0 and n3 > 0:
            d = (np.log(n1 + n2) - np.log(n3)) / np.log(2)
        else:
            d = 1.0

        alpha = np.exp(-4.6 * (d - 1))
        alpha = min(max(alpha, alpha_min), 1.0)

        if i == frama_length - 1 or np.isnan(frama[i - 1]):
            frama[i] = price_arr[i]
        else:
            frama[i] = alpha * price_arr[i] + (1 - alpha) * frama[i - 1]

    return pd.Series(frama, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    frama_length: int = 16,
    atr_band: float = 2.0,
    atr_length: int = 20,
    atr_stop_mult: float = 6.0,
    max_hold_days: int = 60,
    leverage_cap: float = 1.0,
    min_hold_days: int = 1,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: close[t-1] > FRAMA[t-1] + atr_band*ATR(frama_length)[t-1]
    Trend exit: close[t-1] < FRAMA[t-1] - 0.5*atr_band*ATR(frama_length)[t-1]
    Hard stop: close[t] <= entry_price - atr_stop_mult*ATR(atr_length) (at entry)
    Backstop: max_hold_days time-stop (this repo's standard convention,
    since the source's own trend-exit could theoretically hold indefinitely).
    """
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    frama = _frama(df, frama_length)
    atr_frama = _atr(df, frama_length)
    atr_stop_series = _atr(df, atr_length)

    entry_upper = frama + atr_band * atr_frama
    exit_lower = frama - 0.5 * atr_band * atr_frama

    close_arr = close.to_numpy()
    entry_upper_arr = entry_upper.to_numpy()
    exit_lower_arr = exit_lower.to_numpy()
    atr_stop_arr = atr_stop_series.to_numpy()

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    entry_price = None

    for i in range(1, n):
        if in_pos:
            hold_count += 1
            stop_hit = (
                entry_price is not None
                and not np.isnan(atr_stop_arr[i - 1])
                and close_arr[i] <= entry_price - atr_stop_mult * atr_stop_arr[i - 1]
            )
            trend_exit = (
                not np.isnan(exit_lower_arr[i - 1])
                and close_arr[i - 1] < exit_lower_arr[i - 1]
                and hold_count >= min_hold_days
            )
            time_exit = hold_count >= max_hold_days
            if stop_hit or trend_exit or time_exit:
                in_pos = False
                hold_count = 0
                entry_price = None
            else:
                pos.iloc[i] = leverage_cap

        if not in_pos:
            if (
                not np.isnan(entry_upper_arr[i - 1])
                and close_arr[i - 1] > entry_upper_arr[i - 1]
            ):
                in_pos = True
                hold_count = 0
                entry_price = close_arr[i]
                pos.iloc[i] = leverage_cap

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    frama_length: int = 16,
    atr_band: float = 2.0,
    atr_length: int = 20,
    atr_stop_mult: float = 6.0,
    max_hold_days: int = 60,
    leverage_cap: float = 1.0,
    min_hold_days: int = 1,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        frama_length=frama_length,
        atr_band=atr_band,
        atr_length=atr_length,
        atr_stop_mult=atr_stop_mult,
        max_hold_days=max_hold_days,
        leverage_cap=leverage_cap,
        min_hold_days=min_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret

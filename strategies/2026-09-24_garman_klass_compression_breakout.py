"""Strategy: Garman-Klass volatility compression-breakout with ATR direction
and ATR trailing exit.

Hypothesis (knowledge_base id 2026-09-24-003):
Per https://breakingdownfinance.com/finance-topics/risk-management/garman-klass-volatility/
(estimator definition) and https://pinescriptforge.com/strategy/garman-klass-volatility
(disclosed mechanical rule), the Garman-Klass (GK) volatility estimator uses
all four OHLC prices (unlike close-to-close or Parkinson's high/low-only
estimator) to more efficiently estimate realized volatility:

    GK_var = 0.5*(ln(H/L))^2 - (2*ln2 - 1)*(ln(C/O))^2

Source's own disclosed strategy: enter a breakout when GK volatility begins
EXPANDING from a low percentile (i.e. volatility compression followed by
expansion -- a "squeeze" release), with direction determined by the first
1x-ATR breakout of price out of the compression range; exit when GK
volatility peaks and begins contracting, trailing at 1.5x ATR in the
meantime. This is the first Garman-Klass-volatility strategy in this repo
(0 prior KB hits) -- distinct from all prior volatility-regime/vol-percentile
strategies (Bollinger Band Width Percentile, Damiani Volatmeter, Chaikin
Volatility, Historical Volatility Ratio) since none of those use the
4-price (O,H,L,C) Garman-Klass estimator specifically.

Signal logic
------------
- Compute daily GK variance (per the formula above), take a rolling
  smoothed value (SMA over gk_smooth days), and its rolling percentile
  rank over percentile_window days.
- "Compression" = GK percentile <= compression_pctile (source's "low
  percentile" condition).
- On a bar where the asset was in compression within the last
  lookback_days AND GK volatility is now expanding (today's smoothed GK >
  yesterday's, i.e. rising off the compression low) AND price breaks above
  the highest close of the compression window by >= 1x ATR (source's
  "first 1x ATR breakout" direction rule, long-only adaptation): enter long.
- Exit: GK volatility peaks and starts contracting (smoothed GK falls for
  gk_decline_bars consecutive bars), OR price closes below entry_high -
  atr_trail_mult*ATR (the 1.5x-ATR trailing stop, long-only), OR a
  max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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


def _garman_klass_var(df: pd.DataFrame) -> pd.Series:
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    open_ = df["open"] if "open" in df.columns else df["close"]
    close = df["close"]

    log_hl = np.log((high / low).replace(0, np.nan).clip(lower=1e-8))
    log_co = np.log((close / open_).replace(0, np.nan).clip(lower=1e-8))

    gk_var = 0.5 * (log_hl ** 2) - (2 * np.log(2) - 1) * (log_co ** 2)
    gk_var = gk_var.clip(lower=0.0)
    return gk_var


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    gk_smooth: int = 5,
    percentile_window: int = 100,
    compression_pctile: float = 0.20,
    lookback_days: int = 10,
    atr_window: int = 14,
    breakout_atr_mult: float = 1.0,
    atr_trail_mult: float = 1.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    gk_var = _garman_klass_var(df)
    gk_smoothed = gk_var.rolling(gk_smooth).mean()
    gk_pctile = gk_smoothed.rolling(percentile_window).rank(pct=True)

    was_compressed = (gk_pctile <= compression_pctile).rolling(lookback_days).max().fillna(0) > 0
    gk_expanding = gk_smoothed > gk_smoothed.shift(1)

    atr = _atr(df, atr_window)
    compression_high = close.rolling(lookback_days).max()
    breakout_up = close > (compression_high.shift(1) + breakout_atr_mult * atr)

    entry_signal = (was_compressed & gk_expanding & breakout_up).fillna(False).to_numpy()
    gk_declining = (gk_smoothed < gk_smoothed.shift(1)).fillna(False).to_numpy()
    close_arr = close.to_numpy()
    atr_arr = atr.fillna(0.0).to_numpy()

    pos_arr = [0] * n
    in_pos = False
    hold_days = 0
    entry_high = 0.0

    for i in range(n):
        if in_pos:
            hold_days += 1
            entry_high = max(entry_high, close_arr[i])
            trail_stop = entry_high - atr_trail_mult * atr_arr[i]
            if (close_arr[i] < trail_stop) or gk_declining[i] or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
        else:
            if entry_signal[i]:
                in_pos = True
                hold_days = 0
                entry_high = close_arr[i]
        pos_arr[i] = 1 if in_pos else 0

    return pd.Series(pos_arr, index=close.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    gk_smooth: int = 5,
    percentile_window: int = 100,
    compression_pctile: float = 0.20,
    lookback_days: int = 10,
    atr_window: int = 14,
    breakout_atr_mult: float = 1.0,
    atr_trail_mult: float = 1.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        gk_smooth=gk_smooth,
        percentile_window=percentile_window,
        compression_pctile=compression_pctile,
        lookback_days=lookback_days,
        atr_window=atr_window,
        breakout_atr_mult=breakout_atr_mult,
        atr_trail_mult=atr_trail_mult,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret

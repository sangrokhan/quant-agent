"""Strategy: Simplified Empirical Mode Decomposition (EMD) Trend Helix.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per "Empirical Mode Decomposition Trend Helix" (forexobroker,
https://www.tradingview.com/script/yjn4pHMm-Empirical-Mode-Decomposition-
Trend-Helix-forexobroker/, read via browser_exec -- fully disclosed
algorithm and default parameters). Genuinely novel for this repo (0 prior
"Empirical Mode Decomposition"/"EMD"/"intrinsic mode function" hits):
Huang's EMD (Huang et al. 1998) sifts a signal into a trend residual and
oscillatory Intrinsic Mode Functions (IMFs) -- the source's own
"simplified EMD" substitutes rolling-extrema-based envelopes for the
formal method's cubic-spline envelopes (a tractable, from-scratch,
no-new-dependency implementation avoiding the PyEMD package, which is not
installed in this repo's environment):

  1. Rolling local max/min of close over `extrema_window` bars (source
     default 10).
  2. Smooth each into an upper/lower envelope via SMA of length
     `envelope_smooth` (source default 5).
  3. Mean envelope m_t = (upper + lower) / 2 is this sift iteration's trend
     residual.
  4. Repeat the sift for `sift_iterations` rounds (source default 2), using
     the previous m_t as input each round (progressively smoother trend).
  5. IMF1 (high-frequency component) = close - final trend.
  6. Trend direction: linear-slope sign of the final trend over
     `slope_lookback` bars (source default 5), bullish if slope exceeds
     +min_slope.
  7. Signal (long-only, consistent with this repo's convention -- source's
     own short-signal branch omitted): Buy when IMF1 crosses above zero
     AND trend slope is bullish; Exit when IMF1 crosses below zero OR
     trend slope turns bearish (this repo's OR-logic exit convention,
     since the source itself only specifies symmetric buy/sell entry
     triggers, not an explicit long-only exit rule -- exiting on the
     mirror-image condition of the entry is the natural interpretation).
     A `cooldown_bars` parameter (source default 15) suppresses re-entry
     immediately after an exit, matching the source's own cooldown
     mechanism (there to avoid over-trading IMF1's frequent zero-crossings).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _simplified_emd_trend(
    close: pd.Series, extrema_window: int, envelope_smooth: int, sift_iterations: int
) -> pd.Series:
    """Rolling-extrema-based simplified EMD sift, per the source's own
    'simplified EMD' algorithm description (steps 1-4)."""
    signal = close.copy()
    for _ in range(sift_iterations):
        upper = signal.rolling(extrema_window).max()
        lower = signal.rolling(extrema_window).min()
        upper_smooth = upper.rolling(envelope_smooth).mean()
        lower_smooth = lower.rolling(envelope_smooth).mean()
        signal = (upper_smooth + lower_smooth) / 2.0
    return signal


def _trend_slope(trend: pd.Series, slope_lookback: int) -> pd.Series:
    """Simple linear slope: (trend_t - trend_{t-lookback}) / lookback,
    per the source's 'local linear estimate' description."""
    return (trend - trend.shift(slope_lookback)) / slope_lookback


def generate_signals(
    price_df: pd.DataFrame,
    extrema_window: int = 10,
    envelope_smooth: int = 5,
    sift_iterations: int = 2,
    slope_lookback: int = 5,
    min_slope: float = 0.0,
    cooldown_bars: int = 15,
) -> pd.Series:
    """Return a 0/1 long/flat position series. Long when IMF1 (close minus
    the sifted trend) crosses above zero AND the trend's slope is bullish
    (source's own buy signal, long-only adaptation); exit on the mirror
    condition (IMF1 crosses below zero OR trend turns bearish). A cooldown
    period after each exit suppresses immediate re-entry (source's own
    anti-overtrading mechanism)."""
    df = _prep(price_df)
    close = df["close"]

    trend = _simplified_emd_trend(close, extrema_window, envelope_smooth, sift_iterations)
    imf1 = close - trend
    slope = _trend_slope(trend, slope_lookback)

    imf1_prev = imf1.shift(1)
    cross_up = (imf1 > 0) & (imf1_prev <= 0)
    cross_down = (imf1 < 0) & (imf1_prev >= 0)
    bullish_slope = slope > min_slope
    bearish_slope = slope < -min_slope

    buy_signal = (cross_up & bullish_slope).fillna(False).to_numpy()
    exit_signal = (cross_down | bearish_slope).fillna(False).to_numpy()

    n = len(df)
    pos_vals = np.zeros(n, dtype=int)
    in_pos = False
    cooldown_remaining = 0
    for i in range(n):
        if cooldown_remaining > 0:
            cooldown_remaining -= 1
        if in_pos:
            if exit_signal[i]:
                in_pos = False
                cooldown_remaining = cooldown_bars
                pos_vals[i] = 0
            else:
                pos_vals[i] = 1
        else:
            if buy_signal[i] and cooldown_remaining == 0:
                in_pos = True
                pos_vals[i] = 1
            else:
                pos_vals[i] = 0
    return pd.Series(pos_vals, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    extrema_window: int = 10,
    envelope_smooth: int = 5,
    sift_iterations: int = 2,
    slope_lookback: int = 5,
    min_slope: float = 0.0,
    cooldown_bars: int = 15,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        extrema_window=extrema_window,
        envelope_smooth=envelope_smooth,
        sift_iterations=sift_iterations,
        slope_lookback=slope_lookback,
        min_slope=min_slope,
        cooldown_bars=cooldown_bars,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

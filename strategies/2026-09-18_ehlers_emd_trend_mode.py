"""Strategy: Ehlers Empirical Mode Decomposition (EMD) Trend-mode crossover.

Hypothesis (knowledge_base id TBD, this cron trigger):
John F. Ehlers & Ric Way's "Empirical Mode Decomposition" (TASC, March
2010): a bandpass filter (period/delta1-parameterized 2-pole recursive
filter) separates cyclical price movement from noise; the bandpass
output's rolling SMA over 2*period bars is the "Trend" line. The bandpass
series' local peaks and valleys are tracked and each SMA(50)-averaged,
then scaled by a `fraction` multiplier to produce "FracAvgPeak"/
"FracAvgValley" reference bands. Per the widely-republished Pine Script
implementation (https://www.tradingview.com/script/Qy6QFjs2-blackcat-L2-Ehlers-Empirical-Mode-Trader/,
"100% John F. Ehlers definition translation, even variable names are the
same" -- full source code read this iteration via browser_exec, web_search
DDGS backend failing again this cron trigger): in TREND mode, a long
signal fires when Trend crosses above FracAvgPeak (the trend line breaking
out above its own recent bandpass-peak reference band, confirming a
genuine trending regime rather than a noise wiggle); exit/short when Trend
crosses below FracAvgValley. This repo implements only the long side per
SAFETY.md (source's own Cycle mode, using Bollinger Band mean-reversion
inside the [FracAvgValley, FracAvgPeak] band, is a distinct alternate
mode not implemented here -- Trend mode is the more directly
mechanically-testable of the two disclosed modes). Zero prior "Empirical
Mode Decomposition"/"EMD" entries in this repo (confirmed via
strategies_index.jsonl search this iteration).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily returns)
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


def _empirical_mode(
    price: pd.Series,
    period: int = 20,
    delta1: float = 0.5,
    fraction: float = 5.0,
    peak_valley_avg_window: int = 50,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Ehlers/Way Empirical Mode Decomposition bandpass filter + peak/valley
    tracking, per the disclosed Pine Script formula. Returns
    (trend, frac_avg_peak, frac_avg_valley), all aligned to `price`'s index.
    """
    p = price.to_numpy(dtype=float)
    n = len(p)

    pi = np.pi
    beta1 = np.cos(2 * pi / period)
    gamma1 = 1.0 / np.cos(4 * pi * delta1 / period)
    # guard against gamma1^2 - 1 < 0 (degenerate for extreme delta1/period)
    disc = max(gamma1 ** 2 - 1.0, 0.0)
    alpha = gamma1 - np.sqrt(disc)
    half_alpha_diff = 0.5 * (1.0 - alpha)
    beta1_one_plus_alpha = beta1 * (1.0 + alpha)

    bp = np.zeros(n)
    for i in range(n):
        p_im2 = p[i - 2] if i >= 2 else 0.0
        bp_im1 = bp[i - 1] if i >= 1 else 0.0
        bp_im2 = bp[i - 2] if i >= 2 else 0.0
        bp[i] = (
            half_alpha_diff * (p[i] - p_im2)
            + beta1_one_plus_alpha * bp_im1
            - alpha * bp_im2
        )

    bp_series = pd.Series(bp, index=price.index)
    trend = bp_series.rolling(2 * period, min_periods=2 * period).mean()

    # Local peak/valley detection on bp (3-point pivot, using bp[i-1] as the
    # candidate pivot vs its immediate neighbors, matching the disclosed
    # Pine logic: nz(bp[1]) compared against bp (current) and nz(bp[2])).
    peak = np.zeros(n)
    valley = np.zeros(n)
    for i in range(n):
        bp_im1 = bp[i - 1] if i >= 1 else 0.0
        bp_im2 = bp[i - 2] if i >= 2 else 0.0
        bp_i = bp[i]
        if bp_im1 > bp_i and bp_im1 > bp_im2:
            peak[i] = bp_im1
        elif bp_im1 < bp_i and bp_im1 < bp_im2:
            valley[i] = bp_im1

    peak_series = pd.Series(peak, index=price.index)
    valley_series = pd.Series(valley, index=price.index)

    avg_peak = peak_series.rolling(peak_valley_avg_window, min_periods=peak_valley_avg_window).mean()
    avg_valley = valley_series.rolling(peak_valley_avg_window, min_periods=peak_valley_avg_window).mean()

    frac_avg_peak = fraction * avg_peak
    frac_avg_valley = fraction * avg_valley

    return trend, frac_avg_peak, frac_avg_valley


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 20,
    delta1: float = 0.5,
    fraction: float = 5.0,
    peak_valley_avg_window: int = 50,
    max_hold_days: int = 60,
) -> pd.Series:
    """0/1 long-only position series: enter when Trend crosses above
    FracAvgPeak (trending-regime breakout confirmation); exit when Trend
    crosses below FracAvgValley or a max_hold_days time-stop is hit
    (source's own short-side condition is dropped per SAFETY.md long-only
    scope).
    """
    df = _prep(price_df)
    close = df["close"]

    trend, frac_avg_peak, frac_avg_valley = _empirical_mode(
        close, period=period, delta1=delta1, fraction=fraction,
        peak_valley_avg_window=peak_valley_avg_window,
    )

    long_entry = (trend > frac_avg_peak) & (trend.shift(1) <= frac_avg_peak.shift(1))
    long_exit = (trend < frac_avg_valley) & (trend.shift(1) >= frac_avg_valley.shift(1))

    position = np.zeros(len(close))
    in_position = False
    hold_count = 0
    entry_arr = long_entry.fillna(False).to_numpy()
    exit_arr = long_exit.fillna(False).to_numpy()

    for i in range(len(close)):
        if in_position:
            hold_count += 1
            if exit_arr[i] or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
        elif entry_arr[i]:
            in_position = True
            hold_count = 0
        position[i] = 1.0 if in_position else 0.0

    return pd.Series(position, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 20,
    delta1: float = 0.5,
    fraction: float = 5.0,
    peak_valley_avg_window: int = 50,
    max_hold_days: int = 60,
) -> pd.Series:
    """Daily strategy returns: prior-bar position * that bar's return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        period=period,
        delta1=delta1,
        fraction=fraction,
        peak_valley_avg_window=peak_valley_avg_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret

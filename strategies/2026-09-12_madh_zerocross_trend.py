"""Strategy: MADH (Moving Average Difference, Hann-windowed) zero-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
John Ehlers' MAD (Moving Average Difference) oscillator -- MAD =
100*(SMA(price, short)/SMA(price, long) - 1) -- is a "thinking man's MACD"
(TASC Oct 2021 Traders' Tips). Its Hann-windowed sibling MADH applies a Hann
FIR window to each of the two SMAs before differencing:

    MADH = 100 * ( SMA(hann(price, short), short)
                    / SMA(hann(price, long), long) - 1 )

per financial-hacker.com's disclosed Zorro/C transcription (TASC Nov 2021
Traders' Tips, "MADH is an evolutionary update from the prior MAD indicator").
Default periods per Ehlers' own article: short=8, long=23 (analogous to
MACD's 12/26 but tuned so the two SMAs differ by about half the dominant
cycle period, keeping MADH roughly in phase with the market's dominant
cycle).

This iteration's test: MADH crossing above zero (its own basic centerline,
the same interpretation TradingView's official port uses as the "ZeroCross"
coloring mode) signals a fresh short-term uptrend acceleration, gated by a
longer trend filter (close > SMA(trend_window)) to avoid buying MADH's
whipsaws in a downtrend. Exit on MADH crossing back below zero, the trend
filter breaking, or a max_hold_days time-stop.

Distinct from prior repo entries: this is the first MAD/MADH-family strategy
tested in this repo (no matches in strategies_index.jsonl for "MAD"/"MADH").
Different smoothing philosophy from the already-tested Ehlers Hann-RSI
(2026-09-12-148, rejected) and Hann Directional Movement family -- those
apply Hann windowing to an oscillator's *inputs*; here Hann windowing is
applied directly to the two SMAs that are then ratio-differenced, closer in
spirit to a smoothed-MACD than a smoothed-RSI/DMI.

Sources:
  https://www.tradingview.com/scripts/tasc/page-4/ (TASC 2021.11 MADH
    overview -- concept description, no full Pine source shown)
  https://financial-hacker.com/the-mad-indicator/ (exact MAD/MADH formulas
    disclosed in Zorro/C code, corroborating TASC's own October/November
    2021 Traders' Tips articles)

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _hann_weights(n: int) -> np.ndarray:
    """Hann window weights of length n, normalized to sum to 1.

    Ehlers' Hann-windowed FIR filter: w_k = 1 - cos(2*pi*(k+1)/(n+1)) for
    k=0..n-1, normalized so the weighted sum is a true weighted average.
    """
    k = np.arange(1, n + 1)
    w = 1.0 - np.cos(2.0 * np.pi * k / (n + 1))
    w = w / w.sum()
    return w


def _hann_filter(series: pd.Series, length: int) -> pd.Series:
    """Rolling Hann-windowed FIR filter applied to `series`."""
    weights = _hann_weights(length)
    # weights[0] applies to the oldest bar in the window, weights[-1] to the
    # most recent bar (matches a causal FIR filter convention).
    return series.rolling(length).apply(
        lambda x: float(np.dot(x, weights)), raw=True
    )


def _madh(close: pd.Series, short_len: int, long_len: int) -> pd.Series:
    hann_short = _hann_filter(close, short_len)
    hann_long = _hann_filter(close, long_len)
    sma_short = hann_short.rolling(short_len).mean()
    sma_long = hann_long.rolling(long_len).mean()
    madh = 100.0 * (sma_short / sma_long - 1.0)
    return madh


def generate_signals(
    price_df: pd.DataFrame,
    short_len: int = 8,
    long_len: int = 23,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    madh = _madh(close, short_len, long_len)
    trend_sma = close.rolling(trend_window).mean()
    trend_ok = close > trend_sma

    cross_up = (madh > 0) & (madh.shift(1) <= 0)
    cross_down = (madh < 0) & (madh.shift(1) >= 0)

    entry = cross_up & trend_ok.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_now = (
                bool(cross_down.iloc[i])
                or not bool(trend_ok.iloc[i])
                or held >= max_hold_days
            )
            if exit_now:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

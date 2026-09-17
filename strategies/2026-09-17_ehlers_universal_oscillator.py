"""Strategy: Ehlers Universal Oscillator ("Whiter Is Brighter", John F.
Ehlers, TASC January 2015), long-only adaptation. Read this iteration via
browser_exec at https://traders.com/documentation/feedbk_docs/2015/01/traderstips.html
(EasyLanguage code disclosed directly in the article's TradeStation
Traders' Tips code section, credited to Doug McCrary/TradeStation
Securities).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-122):
Ehlers' theory: raw price data resembles PINK noise ("noise with memory"),
so rather than filtering price itself, first convert it to WHITE noise
(WhiteNoise = (Close[t] - Close[t-2]) / 2 -- a simple centered 2-bar
difference, which per Ehlers whitens the pink-noise spectral characteristic
of price) BEFORE applying a SuperSmoother lowpass filter (period=band_edge).
The smoothed white-noise-derivative is then Automatic-Gain-Control (AGC)
normalized via the same fast-attack/slow-decay peak tracker used in the
Quotient Transform article (2026-09-17-121), producing "Universal" in
roughly [-1,1]. Long entry when Universal crosses above 0; exit when it
crosses below 0. This is distinct from the repo's other Ehlers
zero-crossing entries because it filters a WHITENED momentum series
(2-bar price difference) rather than price itself or a highpassed price
series -- Ehlers' own stated rationale for why this indicator should give
a cleaner turning-point signal than his other SuperSmoother-based
constructions.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
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


def _universal_oscillator(close: pd.Series, band_edge: int) -> pd.Series:
    n = len(close)
    c = close.values.astype(float)

    white_noise = np.zeros(n)
    white_noise[2:] = (c[2:] - c[:-2]) / 2.0

    a1 = np.exp(-1.414 * np.pi / band_edge)
    b1 = 2 * a1 * np.cos(np.deg2rad(1.414 * 180.0 / band_edge))
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    filt = np.zeros(n)
    for i in range(1, n):
        prev2 = filt[i - 2] if i >= 2 else 0.0
        filt[i] = c1 * (white_noise[i] + white_noise[i - 1]) / 2.0 + c2 * filt[i - 1] + c3 * prev2

    peak = np.zeros(n)
    peak[0] = 1e-7
    for i in range(1, n):
        peak[i] = 0.991 * peak[i - 1]
        if abs(filt[i]) > peak[i]:
            peak[i] = abs(filt[i])

    universal = np.zeros(n)
    nonzero = peak != 0
    universal[nonzero] = filt[nonzero] / peak[nonzero]

    return pd.Series(universal, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    band_edge: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series per Ehlers' Universal
    Oscillator zero-cross rule (long-only adaptation)."""
    df = _prep(price_df)
    close = df["close"]

    universal = _universal_oscillator(close, band_edge)

    entry = (universal.shift(1) <= 0) & (universal > 0)
    exit_cond = (universal.shift(1) >= 0) & (universal < 0)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if bool(exit_cond.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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

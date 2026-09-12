"""Strategy: Ehlers Ultimate Strength Index (USI) zero-line crossover.

Hypothesis (see knowledge_base entry): per John F. Ehlers' TASC 12/2024
article and its financial-hacker.com writeup
(https://financial-hacker.com/the-ultimate-strength-index/), the USI is a
symmetric (-1..+1), low-lag replacement for RSI built from normalized
smoothed up/down price moves. Being lower-lag than RSI, it should generate
timelier long entries when it crosses from negative to positive (bullish
momentum shift) than a classic RSI-midline crossover, and exit when it
crosses back negative.

Algorithm (fully disclosed by source, using the Ehlers UltimateSmoother
already used elsewhere in this repo, e.g.
2026-09-12_ou_halflife_zscore_smoothed_fix.py):
    up_move   = max(0, close[t] - close[t-1])
    down_move = max(0, close[t-1] - close[t])
    USU = UltimateSmoother(SMA(up_move, 4), length)
    USD = UltimateSmoother(SMA(down_move, 4), length)
    USI = (USU - USD) / (USU + USD)   (0 when denominator is 0)

Long-only adaptation: long while USI > 0, flat while USI <= 0 (zero-line
crossover, mirroring the source's zero-line USI display convention).

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


def _ultimate_smoother(series: pd.Series, length: int) -> pd.Series:
    """Ehlers UltimateSmoother: 2-pole highpass-derived low-lag smoother."""
    n = max(2, int(length))
    f = (1.414 * np.pi) / n
    a1 = np.exp(-f)
    c2 = 2 * a1 * np.cos(f)
    c3 = -a1 * a1
    c1 = (1 + c2 - c3) / 4.0

    vals = series.to_numpy(dtype=float)
    out = np.zeros_like(vals)
    for i in range(len(vals)):
        d0 = vals[i]
        d1 = vals[i - 1] if i >= 1 else d0
        d2 = vals[i - 2] if i >= 2 else d0
        u1 = out[i - 1] if i >= 1 else d0
        u2 = out[i - 2] if i >= 2 else d0
        out[i] = (1 - c1) * d0 + (2 * c1 - c2) * d1 - (c1 + c3) * d2 + c2 * u1 + c3 * u2
    return pd.Series(out, index=series.index)


def _usi(close: pd.Series, length: int) -> pd.Series:
    up_move = (close - close.shift(1)).clip(lower=0).fillna(0.0)
    down_move = (close.shift(1) - close).clip(lower=0).fillna(0.0)

    su_sma = up_move.rolling(4).mean().bfill()
    sd_sma = down_move.rolling(4).mean().bfill()

    usu = _ultimate_smoother(su_sma, length)
    usd = _ultimate_smoother(sd_sma, length)

    denom = (usu + usd).replace(0, np.nan)
    usi = ((usu - usd) / denom).fillna(0.0)
    return usi


def generate_signals(
    price_df: pd.DataFrame,
    usi_length: int = 28,
) -> pd.Series:
    """Long while USI > 0 (zero-line crossover), flat otherwise."""
    df = _prep(price_df)
    close = df["close"]

    usi = _usi(close, usi_length)
    position = (usi > 0).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

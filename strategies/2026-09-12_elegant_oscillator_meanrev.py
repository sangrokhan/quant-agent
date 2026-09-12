"""Strategy: Ehlers Elegant Oscillator (Inverse Fisher Transform) mean reversion.

Hypothesis (see knowledge_base entry): per John F. Ehlers' TASC February
2022 article, reproduced at
https://financial-hacker.com/the-inverse-fisher-transform/ (fully
disclosed C code): the Elegant Oscillator (EO) converts a normalized
2-bar price derivative into the +/-1 range via the Inverse Fisher
Transform, then SuperSmoother-smooths the result. Peaks above a positive
threshold and valleys below a negative threshold should mark short-term
mean-reversion turning points -- short on a peak above +threshold, long
on a valley below -threshold. The source only tested 7 trades on SPY
2020-2021 (positive but statistically thin) and explicitly invited
broader testing -- this repo runs a full grid across parameters, vol
regimes and asset classes instead.

Algorithm (fully disclosed by source):
    deriv[t] = price[t] - price[t-2]
    rms[t] = sqrt(sum(deriv[t-length+1..t]^2) / length)
    norm_deriv[t] = deriv[t] / rms[t]
    ift(x) = (exp(2x) - 1) / (exp(2x) + 1)
    EO[t] = SuperSmoother(ift(norm_deriv), smooth_length)[t]

Long-only adaptation (dropping the short side per this repo's convention):
long when EO forms a valley (local min) below -threshold, exit when EO
crosses back above 0 (mean-reversion target) or a max-hold time-stop.

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


def _super_smoother(series: pd.Series, length: int) -> pd.Series:
    n = max(2, int(length))
    a1 = np.exp(-1.414 * np.pi / n)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / n)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3
    vals = series.to_numpy(dtype=float)
    out = np.zeros_like(vals)
    for i in range(len(vals)):
        v = vals[i]
        p1 = out[i - 1] if i >= 1 else v
        p2 = out[i - 2] if i >= 2 else v
        v0 = vals[i - 1] if i >= 1 else v
        out[i] = c1 * (v + v0) / 2.0 + c2 * p1 + c3 * p2
    return pd.Series(out, index=series.index)


def _elegant_oscillator(close: pd.Series, length: int, smooth_length: int) -> pd.Series:
    deriv = (close - close.shift(2)).fillna(0.0)
    rms = np.sqrt((deriv ** 2).rolling(length, min_periods=5).mean())
    rms = rms.replace(0, np.nan)
    norm_deriv = (deriv / rms).fillna(0.0).clip(-10, 10)

    ift = (np.exp(2 * norm_deriv) - 1) / (np.exp(2 * norm_deriv) + 1)
    eo = _super_smoother(ift, smooth_length)
    return eo


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 20,
    smooth_length: int = 20,
    threshold: float = 0.5,
    max_hold_days: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    eo = _elegant_oscillator(close, length, smooth_length)
    is_valley = (eo.shift(1) > eo) & (eo.shift(-1) > eo)
    entry = is_valley.fillna(False) & (eo < -threshold)
    exit_reversion = eo > 0

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_reversion.iloc[i]) or held >= max_hold_days:
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
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

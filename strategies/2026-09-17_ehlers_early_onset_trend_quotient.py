"""Strategy: Ehlers Early Onset Trend / Quotient Transform ("The Quotient
Transform", John F. Ehlers, TASC August 2014). Read this iteration via
browser_exec at https://traders.com/documentation/feedbk_docs/2014/08/traderstips.html
(EasyLanguage code disclosed directly in the article's TradeStation Traders'
Tips code section, credited to Doug McCrary/TradeStation Securities).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-121):
Ehlers' "Quotient Transform" is a peak-normalization + nonlinear-warp
technique distinct from his other bandpass-filter constructions already
tested in this repo (Roofing Filter crossover-of-own-SMA, MESA Sine Wave,
Correlation Cycle, etc.): a 2-pole highpass filter strips cycles longer
than 100 bars, then a SuperSmoother lowpass filter (period=LPPeriod)
denoises the highpassed series into Filt. A "fast attack, slow decay" peak
tracker (Peak decays 0.991x/bar unless |Filt| exceeds it) normalizes Filt
into X (roughly [-1,1]). Two DIFFERENT quotient (Mobius-like) transforms
are then applied to the SAME normalized X with different warp constants K1
(0.85, a "faster" warp for the buy signal) and K2 (0.4, a "slower" warp for
the sell signal) -- Quotient=(X+K)/(K*X+1) -- producing two asymmetrically
warped zero-crossing lines instead of one. The source's own disclosed
strategy rule is genuinely asymmetric: LONG entry on Quotient1 (K1=0.85)
crossing above zero, exit on Quotient2 (K2=0.4) crossing below zero -- two
DIFFERENT thresholds/warps for entry vs exit of the SAME underlying
normalized-and-smoothed trend signal, intended to give the trend detector
an early (fast) entry trigger and a separately-tuned (slower, more patient)
exit trigger. This is distinct from the repo's other Ehlers entries because
none use this dual-asymmetric-quotient-warp entry/exit construction.

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


def _early_onset_quotients(close: pd.Series, lp_period: int, k1: float, k2: float):
    n = len(close)
    c = close.values.astype(float)

    alpha1 = (np.cos(np.deg2rad(0.707 * 360.0 / 100.0)) + np.sin(np.deg2rad(0.707 * 360.0 / 100.0)) - 1.0) / np.cos(
        np.deg2rad(0.707 * 360.0 / 100.0)
    )

    hp = np.zeros(n)
    for i in range(2, n):
        hp[i] = (
            (1 - alpha1 / 2) ** 2 * (c[i] - 2 * c[i - 1] + c[i - 2])
            + 2 * (1 - alpha1) * hp[i - 1]
            - (1 - alpha1) ** 2 * hp[i - 2]
        )

    a1 = np.exp(-1.414 * np.pi / lp_period)
    b1 = 2 * a1 * np.cos(np.deg2rad(1.414 * 180.0 / lp_period))
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    filt = np.zeros(n)
    for i in range(2, n):
        filt[i] = c1 * (hp[i] + hp[i - 1]) / 2.0 + c2 * filt[i - 1] + c3 * filt[i - 2]

    peak = np.zeros(n)
    for i in range(1, n):
        peak[i] = 0.991 * peak[i - 1]
        if abs(filt[i]) > peak[i]:
            peak[i] = abs(filt[i])

    x = np.zeros(n)
    nonzero = peak != 0
    x[nonzero] = filt[nonzero] / peak[nonzero]

    quotient1 = (x + k1) / (k1 * x + 1.0)
    quotient2 = (x + k2) / (k2 * x + 1.0)

    idx = close.index
    return pd.Series(quotient1, index=idx), pd.Series(quotient2, index=idx)


def generate_signals(
    price_df: pd.DataFrame,
    lp_period: int = 30,
    k1: float = 0.85,
    k2: float = 0.4,
) -> pd.Series:
    """Return a {0,1} long/flat position series per Ehlers' Early Onset
    Trend dual-quotient zero-cross rule (long-only)."""
    df = _prep(price_df)
    close = df["close"]

    quotient1, quotient2 = _early_onset_quotients(close, lp_period, k1, k2)

    entry = (quotient1.shift(1) <= 0) & (quotient1 > 0)
    exit_cond = (quotient2.shift(1) >= 0) & (quotient2 < 0)

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

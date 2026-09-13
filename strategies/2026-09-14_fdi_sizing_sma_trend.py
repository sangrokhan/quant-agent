"""Strategy: SMA(trend_window) directional gate with continuous Fractal
Dimension Index (FDI) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-109):
Fractal Dimension Index (Benoit Mandelbrot, popularized for trading via
Ehlers/quant-trading literature): measures how "fractal"/self-similar a
price series is over a rolling window, natively bounded [1.0, 2.0] --
values near 1.0 = straight-line directional trend, near 2.0 = maximally
noisy/ranging, ~1.5 is the trending/ranging threshold. Confirmed via Google
SERP + quantifiedstrategies.com + prorealcode.com (browser_exec fallback
after `web_search` failed 3x with a DDGSException connection error to
search.yahoo.com) -- these sources confirm the [1,2] range and thresholds
but the exact box-counting formula is paywalled/proprietary, so this
iteration reuses the same standard two-segment Ehlers/Mandelbrot
approximation already implemented in this repo's prior FDI entry
(2026-09-08-015: `strategies/2026-09-08_fdi_gated_sma_crossover.py`, a
binary trend-strength REGIME GATE for an SMA crossover, rejected).

Unlike that prior binary-gate use, this iteration reframes FDI as a
CONTINUOUS SIZING dial: since FDI is natively bounded [1,2] like VHF/CHOP
(the pure trend-efficiency family that has repeatedly generalized well to
BOTH equity and crypto this cron trigger, unlike the momentum/volume-flow
family EFI/EMV/STC/Qstick which failed crypto 4x in a row), FDI is rescaled
to [-1,1] via -(FDI-1.5)/0.5 (low FDI = strong trend = high positive
exposure) with no z-score/tanh needed, then used as a CONTINUOUS SIZING dial
within an SMA(trend_window) uptrend gate.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fractal_dimension_index(high: pd.Series, low: pd.Series, window: int) -> pd.Series:
    """Two-segment box-counting FDI approximation, standard construction
    (same as strategies/2026-09-08_fdi_gated_sma_crossover.py).

    window must be even; each rolling window is split into two equal
    halves, and each half's "length" is measured as the (high-low) range
    normalized by half-window bar count. FDI = (log(L1+L2) - log(L)) / log(2),
    clipped to the theoretical [1.0, 2.0] range.
    """
    if window % 2 != 0:
        window += 1
    half = window // 2

    n = len(high)
    hi = high.values.astype(float)
    lo = low.values.astype(float)
    fdi = np.full(n, np.nan)

    for t in range(window - 1, n):
        seg = slice(t - window + 1, t + 1)
        seg1 = slice(t - window + 1, t - window + 1 + half)
        seg2 = slice(t - half + 1, t + 1)

        def _len(hi_slice, lo_slice, m):
            rng = float(np.max(hi_slice) - np.min(lo_slice))
            return rng / m if m > 0 else 0.0

        n1 = _len(hi[seg1], lo[seg1], half)
        n2 = _len(hi[seg2], lo[seg2], half)
        n3 = _len(hi[seg], lo[seg], window)

        if n1 <= 0 or n2 <= 0 or n3 <= 0:
            fdi[t] = np.nan
            continue
        val = (math.log(n1 + n2) - math.log(n3)) / math.log(2)
        fdi[t] = min(max(val, 1.0), 2.0)

    return pd.Series(fdi, index=high.index)


def _fdi_signal(df: pd.DataFrame, fdi_window: int = 30) -> pd.Series:
    """FDI rescaled to [-1, 1] via -(FDI-1.5)/0.5. Low FDI (near 1.0,
    strong directional trend) -> +1; high FDI (near 2.0, ranging/choppy)
    -> -1."""
    fdi = _fractal_dimension_index(df["high"], df["low"], window=fdi_window)
    return -(fdi - 1.5) / 0.5


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    fdi_window: int = 30,
    base_exposure: float = 0.5,
    fdi_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    fdi_sig = _fdi_signal(df, fdi_window=fdi_window)

    raw_exposure = base_exposure + fdi_sensitivity * fdi_sig
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    fdi_window: int = 30,
    base_exposure: float = 0.5,
    fdi_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        fdi_window=fdi_window,
        base_exposure=base_exposure,
        fdi_sensitivity=fdi_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

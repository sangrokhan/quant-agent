"""Strategy: SMA(trend_window) directional gate with continuous Fractal
Energy (FE) volatility-regime sizing overlay + deadband, leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-15-036, this cron trigger):
Fractal Energy (FE), per Google's AI-overview summary (visited this
iteration, citing the "Fractal Energy Indicator Guide" family of sources):
  FE[t] = 100 * StdDev(close, N) / (HighestHigh(N) - LowestLow(N))

Distinct from this repo's existing fractal-family indicators: Fractal
Dimension Index (Mandelbrot box-counting, 2026-09-08-015/2026-09-14-109),
Polarized Fractal Efficiency (net-change/path-length ratio,
2026-09-05-014/2026-09-14-102), and FRAMA (fractal-dimension-adaptive EMA
smoothing, multiple prior entries) -- Fractal Energy is a StdDev-to-range
ratio, a genuinely new construction despite the shared "fractal" family
name. Low FE means price is tightly bound/consolidating within its recent
range (low realized dispersion relative to the extreme range); high FE
means price action has genuine dispersion/energy for a sustained move.
The source's own trading strategy: establish trend direction with a
separate filter, then use low FE (compression/exhaustion) as a setup and
rising FE (energy release) as a breakout-continuation trigger in the
trend's direction.

Rather than a discrete low/high FE threshold-cross rule, this reuses the
cron trigger's established continuous-sizing-dial pattern (as used for the
similarly volatility-regime-flavored Damiani Volatmeter, 2026-09-15-032,
this same trigger): FE is rolling z-scored over `zscore_window` and
tanh-squashed into [-1,+1] as an exposure multiplier -- positive/rising FE
(expanding energy) scales exposure up, low/falling FE (compression) scales
exposure down -- inside an SMA(trend_window) uptrend gate for direction,
with a deadband to cut turnover.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _fractal_energy(df: pd.DataFrame, period: int) -> pd.Series:
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]

    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    price_range = (hh - ll).replace(0.0, np.nan)
    std = close.rolling(period).std()

    fe = 100.0 * std / price_range
    return fe


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
    period: int = 14,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Fractal Energy (StdDev/Range ratio, unbounded but typically small) is
    rolling z-scored over `zscore_window` and tanh-squashed to [-1,+1]
    before use as a sizing dial, gated by an SMA(trend_window) uptrend
    filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    fe = _fractal_energy(df, period)

    roll_mean = fe.rolling(zscore_window).mean()
    roll_std = fe.rolling(zscore_window).std()
    zscore = (fe - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    period: int = 14,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        period=period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

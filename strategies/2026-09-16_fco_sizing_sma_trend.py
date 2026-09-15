"""Strategy: SMA(trend_window) directional gate with continuous Fractal
Chaos Oscillator (FCO) sizing overlay + deadband, leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-16-050, this cron trigger):
Fractal Chaos Oscillator (FCO), per LightningChart/TradingView (Google
AI-overview synthesis via browser_exec Google fallback): FCO =
(close[t] - close[t-n]) / sum(|close.diff()|, n) over an n-period lookback
(n=5 in the source's typical construction). Unlike Kaufman's (unsigned)
Efficiency Ratio -- already tested as a continuous sizing dial in this repo
(id 2026-09-14-111, accepted QQQ/SPY, rejected crypto) -- FCO's numerator
is SIGNED net price change (not absolute), so FCO itself carries direction
as well as magnitude: values near +1 indicate a strong, efficient uptrend,
near -1 a strong efficient downtrend, near 0 chaotic/range-bound
conditions. Per the source's own trading rule, a high positive FCO signals
a buy, a low negative FCO signals a sell/exit. First Fractal-Chaos-
Oscillator-specific strategy in this repo (distinct from the already-tested
unsigned Efficiency Ratio family and from Fractal Chaos Bands/Fractal
Dimension Index/Fractal Energy, separate fractal-family indicators).

Construction (continuous sizing dial): FCO is already naturally bounded to
[-1,+1] (no z-score needed) and, unlike prior efficiency-ratio dials, is
signed -- so it is used directly as the sizing dial (positive FCO scales
exposure up, negative scales it down/to zero) inside an SMA(trend_window)
uptrend gate (retained for directional-bias consistency with this repo's
established pattern, even though FCO itself is signed) with a deadband to
cut turnover.

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


def _fco(close: pd.Series, n: int) -> pd.Series:
    """Fractal Chaos Oscillator: signed net change over n periods divided
    by the sum of absolute bar-to-bar changes over the same window.
    """
    price_diff = close - close.shift(n)
    fractal_length = close.diff().abs().rolling(n).sum()
    fco = price_diff / fractal_length.replace(0.0, np.nan)
    return fco.clip(lower=-1.0, upper=1.0)


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
    fco_window: int = 5,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    FCO (signed, naturally bounded to [-1,+1] over `fco_window` bars) is
    used directly as a sizing dial, gated by an SMA(trend_window) uptrend
    filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    dial = _fco(close, fco_window).fillna(0.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    fco_window: int = 5,
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
        fco_window=fco_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

"""Strategy: SMA(trend_window) directional gate with continuous Trend
Detection Index (TDI, M.H. Pee) sizing overlay + deadband,
leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-16-046, this cron trigger):
Trend Detection Index (TDI, M.H. Pee), exact formula per the R `TTR`
package documentation (https://search.r-project.org/CRAN/refmans/TTR/html/TDI.html,
visited this iteration): momentum[t] = close[t] - close[t-n]. Let S1 =
n-day sum of momentum, S2 = n-day sum of |momentum|. TDI = |S1| -
(multiple*S2 - S2) = |S1| - (multiple-1)*S2. The Direction Indicator (DI)
is the n-day sum of momentum (same quantity as S1, signed). Per the
source: positive TDI signals a trend is underway, negative signals
consolidation/chop; positive DI signals an uptrend, negative a downtrend.
Note: TDI (Trend Detection Index) is a distinct indicator from "TDI"
(Traders Dynamic Index, Dean Malone), already tested multiple times in
this repo -- this is the first Trend-Detection-Index-specific strategy.

Construction (continuous sizing dial from the start, following this cron
trigger's established pattern rather than testing a discrete threshold
first): TDI itself (trend-strength magnitude, positive=trending) is
rolling z-scored and tanh-squashed into [-1,+1], used as a continuous
sizing dial -- higher TDI (stronger/cleaner trend) scales exposure up,
lower/negative TDI (consolidation/chop) scales exposure down -- inside an
SMA(trend_window) uptrend gate (for directional bias) with a deadband to
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


def _tdi(close: pd.Series, n: int, multiple: float) -> pd.Series:
    """Trend Detection Index (M.H. Pee): TDI = |S1| - (multiple-1)*S2,
    where S1 = n-day sum of n-day momentum, S2 = n-day sum of |momentum|.
    """
    momentum = close.diff(n)
    s1 = momentum.rolling(n).sum()
    s2 = momentum.abs().rolling(n).sum()
    tdi = s1.abs() - (multiple - 1.0) * s2
    return tdi


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
    tdi_n: int = 20,
    tdi_multiple: float = 2.0,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    TDI (trend-strength magnitude) is rolling z-scored over
    `zscore_window` and tanh-squashed to [-1,+1] before use as a sizing
    dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    tdi = _tdi(close, tdi_n, tdi_multiple)

    roll_mean = tdi.rolling(zscore_window).mean()
    roll_std = tdi.rolling(zscore_window).std()
    zscore = (tdi - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    tdi_n: int = 20,
    tdi_multiple: float = 2.0,
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
        tdi_n=tdi_n,
        tdi_multiple=tdi_multiple,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

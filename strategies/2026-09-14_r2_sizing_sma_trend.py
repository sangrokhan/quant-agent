"""Strategy: SMA(trend_window) directional gate with continuous R-squared
(linear regression goodness-of-fit) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-113):
R-squared (coefficient of determination): R^2 = 1 - SS_res/SS_tot for an
n-period rolling least-squares linear regression fit of price vs. time,
natively bounded [0, 1]. Confirmed via Google SERP (browser_exec
navigation): Investopedia/Wikipedia/statisticsfundamentals.com all confirm
the standard [0,1] goodness-of-fit definition. R^2 near 1 = price tracks its
own linear trend line very tightly (clean, low-noise trend); R^2 near 0 =
price scatters widely around any linear fit (noisy/directionless).

Repo has 1 prior R-squared entry (2026-09-08-054): used as a goodness-of-fit
WEIGHTING multiplier on top of a separate linear-regression-slope zero-line
crossover signal, accepted QQQ+SPY. This iteration instead uses R^2 ALONE
(unsigned, like VHF/ER/CHOP -- an unsigned trend-strength dial, not
combined with a slope-direction signal) as a CONTINUOUS SIZING dial within
an SMA(trend_window) uptrend gate: the SMA gate supplies the direction,
R^2 supplies the "how clean is this trend" sizing signal, testing whether
R^2 in isolation (rather than as a slope-signal weight) still adds value.

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


def _rolling_r_squared(close: pd.Series, window: int) -> pd.Series:
    """Rolling R^2 of an n-period least-squares linear regression fit of
    close price vs. time index, bounded [0, 1]."""
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    def _r2(y: np.ndarray) -> float:
        y_mean = y.mean()
        ss_tot = ((y - y_mean) ** 2).sum()
        if ss_tot <= 0:
            return 0.0
        slope = ((x - x_mean) * (y - y_mean)).sum() / x_var
        intercept = y_mean - slope * x_mean
        y_fit = intercept + slope * x
        ss_res = ((y - y_fit) ** 2).sum()
        r2 = 1.0 - (ss_res / ss_tot)
        return min(max(r2, 0.0), 1.0)

    return close.rolling(window).apply(_r2, raw=True)


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
    r2_window: int = 20,
    base_exposure: float = 0.3,
    r2_sensitivity: float = 0.7,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover. R^2 is already
    bounded [0,1] and unsigned (a trend-quality dial, not a directional
    dial), so exposure = base + sensitivity * R^2, clipped, only applied
    within the SMA uptrend gate."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    r2 = _rolling_r_squared(close, window=r2_window)

    raw_exposure = base_exposure + r2_sensitivity * r2
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    r2_window: int = 20,
    base_exposure: float = 0.3,
    r2_sensitivity: float = 0.7,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        r2_window=r2_window,
        base_exposure=base_exposure,
        r2_sensitivity=r2_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

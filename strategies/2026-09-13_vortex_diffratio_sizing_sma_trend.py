"""Strategy: SMA(trend_window) directional gate with continuous Vortex
Indicator DIFFERENCE-RATIO sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-095):
Vortex Indicator (VI+/VI-, Etienne Botes & Douglas Siepman 2010; formula per
https://en.wikipedia.org/wiki/Vortex_indicator and
https://www.investopedia.com/terms/v/vortex-indicator-vi.asp: VM+ = |high -
prior_low|, VM- = |low - prior_high|, TR = true range, VI+ =
SMA(VM+,n)/SMA(TR,n), VI- = SMA(VM-,n)/SMA(TR,n)). This repo has 4+ prior
Vortex entries (2026-09-04-040, 2026-09-06-091, 2026-09-09-084,
2026-09-11-107/-132), ALL binary crossover/threshold ENTRY triggers (VI+
crosses above VI-, or VI absolute level > 1.0). Individually VI+ and VI- are
NOT cleanly bounded (values can exceed 1 in high-volatility TR-compression
periods), so unlike CMF/VZO/ADX/DMI-diff/CHOP (all natively bounded and
already validated as continuous sizing dials this cron trigger), Vortex
cannot be used directly as a sizing dial. This iteration instead applies the
SAME continuous-sizing construction to a NEW bounded transform:
diff_ratio = (VI+ - VI-) / (VI+ + VI-), algebraically bounded in [-1, 1]
(since VI+, VI- >= 0), analogous to how DMI-diff (2026-09-13-093) turned
Wilder's +DI/-DI into a signed sizing dial -- but built on the structurally
distinct Vortex true-range/high-low-shift construction (Botes & Siepman)
rather than Wilder's smoothed directional movement. Within the
SMA(trend_window) uptrend gate, exposure scales up when diff_ratio is
strongly positive (VI+ dominates VI-, strong/clean uptrend momentum) and
scales down toward zero as diff_ratio falls toward/below zero (VI- closing
the gap, momentum fading), even while the SMA gate stays nominally long.

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


def _vortex_diff_ratio(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """(VI+ - VI-) / (VI+ + VI-), bounded [-1, 1]."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prior_low = low.shift(1)
    prior_high = high.shift(1)
    prior_close = close.shift(1)

    vm_plus = (high - prior_low).abs()
    vm_minus = (low - prior_high).abs()

    tr = pd.concat(
        [
            high - low,
            (high - prior_close).abs(),
            (low - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    tr_sum = tr.rolling(window).sum().replace(0, np.nan)
    vi_plus = vm_plus.rolling(window).sum() / tr_sum
    vi_minus = vm_minus.rolling(window).sum() / tr_sum

    denom = (vi_plus + vi_minus).replace(0, np.nan)
    diff_ratio = (vi_plus - vi_minus) / denom
    return diff_ratio.clip(lower=-1.0, upper=1.0)


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
    vortex_window: int = 14,
    base_exposure: float = 0.5,
    diff_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    diff_ratio = _vortex_diff_ratio(df, window=vortex_window)

    raw_exposure = base_exposure + diff_sensitivity * diff_ratio
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    vortex_window: int = 14,
    base_exposure: float = 0.5,
    diff_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        vortex_window=vortex_window,
        base_exposure=base_exposure,
        diff_sensitivity=diff_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

"""Strategy: SMA(short trend_window) trend-following gate with continuous
DMI-Diff (signed +DI minus -DI) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-093):
Direct follow-up to this cron trigger's ADX sizing dial (2026-09-13-092),
which used the UNSIGNED trend-conviction magnitude only. Wilder's
Directional Movement Index also produces +DI and -DI (the two directional
indicators ADX itself is derived from, via DX=100*|+DI--DI|/(+DI+-DI)),
each individually bounded roughly [0,100]. This iteration uses the SIGNED
difference DMI_diff = (+DI - -DI), bounded roughly [-100,100], as a
CONTINUOUS SIZING dial that combines DIRECTION and MAGNITUDE in one signal
(unlike ADX which is direction-agnostic, and unlike the 8 prior directional
oscillators which don't derive from the same smoothed True-Range-normalized
directional-movement construction Wilder designed specifically to measure
trend). exposure = clip(base_exposure + dmi_sensitivity*(dmi_diff/dmi_ref),
0, leverage_cap) within the SMA(trend_window) gate -- exposure rises as
+DI dominates -DI more strongly (a more one-sided, higher-conviction
uptrend), falls as the two di's converge (indecisive/choppy).

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


def _dmi_diff(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Signed DMI difference: +DI - -DI, bounded roughly [-100, 100]."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prior_close = close.shift(1)

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    tr = pd.concat(
        [
            high - low,
            (high - prior_close).abs(),
            (low - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean() / atr.replace(0, np.nan)
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean() / atr.replace(0, np.nan)

    return plus_di - minus_di


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
    dmi_window: int = 14,
    dmi_reference: float = 25.0,
    base_exposure: float = 0.8,
    dmi_sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    dmi_diff = _dmi_diff(df, window=dmi_window)

    raw_exposure = base_exposure + dmi_sensitivity * (dmi_diff / dmi_reference)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    dmi_window: int = 14,
    dmi_reference: float = 25.0,
    base_exposure: float = 0.8,
    dmi_sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        dmi_window=dmi_window,
        dmi_reference=dmi_reference,
        base_exposure=base_exposure,
        dmi_sensitivity=dmi_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

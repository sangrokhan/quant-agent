"""Strategy: SMA(trend_window) directional gate with continuous Polarized
Fractal Efficiency (PFE) sizing overlay + deadband -- CRYPTO LEVERAGE-CAP
RECALIBRATION of 2026-09-14-102.

Hypothesis (knowledge_base id TBD, this cron trigger):
2026-09-14-102 (PFE continuous sizing dial on SMA(trend_window) trend
gate) accepted decisively on equity (QQQ+SPY, all 5 validators) but was
rejected on crypto with MDD "pinned" at 29.6-30.7% across every deadband
tried (0.25-0.30), never budging below the 25% ceiling despite strong
Sharpe (1.42-1.45) and TC-survival (1.25-1.30) -- explicitly noted in the
prior log entry as resistant to deadband widening alone, i.e. the fix
needed was a tighter exposure ceiling (leverage_cap), not a wider deadband.
This entry applies this repo's now-repeatedly-validated leverage-cap-aware
retune pattern: cut leverage_cap to 0.3, scale down base_exposure and
deadband proportionally so the dial's shape (PFE-normalized sizing signal)
is preserved but its ceiling is capped tightly enough for crypto's higher
realized vol to pull MDD back under 25% while retaining the strong crypto
Sharpe. Formula/source unchanged from 2026-09-14-102 (Hans Hannula 1994;
read directly from Investopedia via browser_exec) -- no new external fetch
needed for this crypto-only recalibration sub-step.

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


def _pfe(close: pd.Series, period: int = 10, smoothing_period: int = 5) -> pd.Series:
    """Polarized Fractal Efficiency, bounded ~[-100, 100]."""
    n = period
    straight_line = np.sqrt((close - close.shift(n)) ** 2 + n ** 2)

    step_dist = np.sqrt((close - close.shift(1)) ** 2 + 1.0)
    path_length = step_dist.rolling(n - 1).sum()

    p = 100.0 * straight_line / path_length.replace(0, np.nan)

    down_day = close < close.shift(1)
    p = p.where(~down_day.fillna(False), -p)

    pfe = p.ewm(span=smoothing_period, adjust=False).mean()
    return pfe.clip(lower=-100.0, upper=100.0)


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
    pfe_period: int = 10,
    pfe_smoothing: int = 5,
    base_exposure: float = 0.15,
    pfe_sensitivity: float = 0.6,
    leverage_cap: float = 0.3,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pfe = _pfe(close, period=pfe_period, smoothing_period=pfe_smoothing)
    pfe_norm = pfe / 100.0  # rescale to roughly [-1, 1]

    raw_exposure = base_exposure + pfe_sensitivity * pfe_norm * leverage_cap
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    pfe_period: int = 10,
    pfe_smoothing: int = 5,
    base_exposure: float = 0.15,
    pfe_sensitivity: float = 0.6,
    leverage_cap: float = 0.3,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        pfe_period=pfe_period,
        pfe_smoothing=pfe_smoothing,
        base_exposure=base_exposure,
        pfe_sensitivity=pfe_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

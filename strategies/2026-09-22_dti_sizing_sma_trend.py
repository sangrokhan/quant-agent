"""Strategy: DTI (Directional Trend Index) as a continuous sizing dial.

Direct fix / extension attempt for this cron trigger's ungated DTI entries
(2026-09-22-023 zero-line-crossover binary signal, SPY accepted/QQQ
near-miss rejected/crypto decisively rejected; 2026-09-22-024 vol-gate
rescue also rejected/falsified). DTI is naturally bounded to roughly
[-100,+100] by construction (a ratio of two triple-smoothed EMAs of the
Composite High/Low Momentum, see 2026-09-22-023's notes for the full
formula derivation from https://www.mql5.com/en/code/384 and
https://www.mql5.com/en/code/382). Rather than a binary zero-line-crossover
entry/exit, this reframes DTI/100 (already bounded [-1,+1]) as a CONTINUOUS
exposure-sizing dial within an SMA(trend_window) uptrend gate, following
this repo's established binary-to-continuous-sizing-dial rescue pattern
(DPO, Hurst, VHF, TII, RVI, CBOE SKEW, VPT, Disparity Index, Stacked-MA,
Reversion Index, Continuation Index, Adaptive SuperSmoother, DSS Bressert,
Kase Peak Oscillator -- all already tested this way in this repo). First
DTI continuous-sizing-dial variant in this repo.

Signal logic
------------
- Trend gate: close > SMA(trend_window) (long-only bias).
- Exposure dial: base_exposure + sensitivity * (DTI/100), clipped to
  [0, leverage_cap]. A deadband around zero DTI avoids churn on noise.
- Flat whenever the SMA trend gate is off.

Interface contract for validators (see validation/validators.py) and the
grid tester (see validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position;
        thresholded version of the continuous dial for compatibility with
        the paper-trading simulator and walk-forward helper)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy
        returns using the CONTINUOUS exposure dial, not the thresholded
        position series)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _triple_ema(series: pd.Series, r: int, s: int, u: int) -> pd.Series:
    e1 = series.ewm(span=r, min_periods=r, adjust=False).mean()
    e2 = e1.ewm(span=s, min_periods=s, adjust=False).mean()
    e3 = e2.ewm(span=u, min_periods=u, adjust=False).mean()
    return e3


def _dti(
    high: pd.Series,
    low: pd.Series,
    q: int = 2,
    r: int = 20,
    s: int = 5,
    u: int = 3,
) -> pd.Series:
    hmu = (high - high.shift(q - 1)).clip(lower=0.0)
    lmd = (-(low - low.shift(q - 1))).clip(lower=0.0)
    hlm = hmu - lmd

    smoothed_hlm = _triple_ema(hlm, r, s, u)
    smoothed_abs_hlm = _triple_ema(hlm.abs(), r, s, u)

    dti = 100.0 * smoothed_hlm / smoothed_abs_hlm.replace(0.0, 1e-12)
    return dti


def _exposure_dial(
    price_df: pd.DataFrame,
    q: int = 2,
    r: int = 20,
    s: int = 5,
    u: int = 3,
    trend_window: int = 40,
    base_exposure: float = 0.5,
    sensitivity: float = 0.6,
    deadband: float = 0.1,
    leverage_cap: float = 1.0,
) -> pd.Series:
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    dti = _dti(high, low, q, r, s, u)
    dti_centered = (dti / 100.0).clip(-1.0, 1.0)
    dti_centered = dti_centered.where(dti_centered.abs() >= deadband, 0.0)

    sma = close.rolling(trend_window).mean()
    trend_gate = close > sma

    exposure = base_exposure + sensitivity * dti_centered
    exposure = exposure.clip(lower=0.0, upper=leverage_cap)
    exposure = exposure.where(trend_gate.fillna(False), 0.0)
    return exposure.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    q: int = 2,
    r: int = 20,
    s: int = 5,
    u: int = 3,
    trend_window: int = 40,
    base_exposure: float = 0.5,
    sensitivity: float = 0.6,
    deadband: float = 0.1,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Thresholded {0,1} position series (exposure > 0 -> long)."""
    exposure = _exposure_dial(
        price_df, q, r, s, u, trend_window, base_exposure, sensitivity, deadband, leverage_cap
    )
    return (exposure > 0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    q: int = 2,
    r: int = 20,
    s: int = 5,
    u: int = 3,
    trend_window: int = 40,
    base_exposure: float = 0.5,
    sensitivity: float = 0.6,
    deadband: float = 0.1,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Continuous-exposure-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = _exposure_dial(
        price_df, q, r, s, u, trend_window, base_exposure, sensitivity, deadband, leverage_cap
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strategy_ret

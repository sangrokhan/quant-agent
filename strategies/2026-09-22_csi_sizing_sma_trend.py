"""Strategy: CSI (Commodity Selection Index) as a continuous sizing dial.

Direct fix attempt for this cron trigger's own prior rejection
(2026-09-22-026, CSI discrete percentile-rank regime gate): full-sample
Sharpe failed on all 4 symbols despite a decent grid pass_fraction (0.370).
That entry's own notes suggested combining the CSI regime signal with this
repo's already-accepted plain-ADXR continuous-sizing-dial construction
(2026-09-16-054) instead of a discrete percentile-rank threshold. This
iteration reframes CSI's own rolling z-score (tanh-squashed to [-1,1],
following this repo's standard continuous-sizing-dial normalization
pattern for unbounded indicators) as a continuous exposure dial within an
SMA(trend_window) uptrend gate, rather than a binary regime-gate/no-gate
switch. Source unchanged: https://www.prorealcode.com/prorealtime-indicators/wilders-csi-commodity-selection-index/,
https://forex-indicators.net/trend-indicators/commodity-selection-index.

Signal logic
------------
- Trend gate: close > SMA(trend_window) (long-only bias).
- Exposure dial: base_exposure + sensitivity * tanh(z-score(CSI, zscore_window)),
  clipped to [0, leverage_cap], with a deadband around zero.
- Flat whenever the SMA trend gate is off.

Interface contract for validators (see validation/validators.py) and the
grid tester (see validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} thresholded position)
    generate_returns(price_df, **params) -> pd.Series   (continuous-exposure daily returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _adxr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr.replace(0.0, 1e-12)
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr.replace(0.0, 1e-12)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, 1e-12)
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    adxr = (adx + adx.shift(period)) / 2.0
    return adxr


def _csi(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
    mm: int = 3,
) -> pd.Series:
    prev_close = close.shift(1)
    price_range = high - low
    a = price_range / prev_close
    b = (high - prev_close).abs() / prev_close
    c = (low - prev_close).abs() / prev_close
    tr_balanced = 100.0 * pd.concat([a, b, c], axis=1).max(axis=1)
    atr_balanced = tr_balanced.rolling(mm).mean()

    adxr = _adxr(high, low, close, period)
    csi = adxr * atr_balanced
    return csi


def _exposure_dial(
    price_df: pd.DataFrame,
    period: int = 14,
    mm: int = 3,
    trend_window: int = 40,
    zscore_window: int = 126,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    deadband: float = 0.1,
    leverage_cap: float = 1.0,
) -> pd.Series:
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    csi = _csi(high, low, close, period, mm)
    csi_mean = csi.rolling(zscore_window).mean()
    csi_std = csi.rolling(zscore_window).std()
    csi_z = (csi - csi_mean) / csi_std.replace(0.0, 1e-12)
    csi_tanh = csi_z.apply(lambda x: (2.0 / (1.0 + pow(2.718281828, -2.0 * x)) - 1.0) if pd.notna(x) else 0.0)
    csi_tanh = csi_tanh.where(csi_tanh.abs() >= deadband, 0.0)

    sma = close.rolling(trend_window).mean()
    trend_gate = close > sma

    exposure = base_exposure + sensitivity * csi_tanh
    exposure = exposure.clip(lower=0.0, upper=leverage_cap)
    exposure = exposure.where(trend_gate.fillna(False), 0.0)
    return exposure.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 14,
    mm: int = 3,
    trend_window: int = 40,
    zscore_window: int = 126,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    deadband: float = 0.1,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Thresholded {0,1} position series (exposure > 0 -> long)."""
    exposure = _exposure_dial(
        price_df, period, mm, trend_window, zscore_window, base_exposure, sensitivity, deadband, leverage_cap
    )
    return (exposure > 0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 14,
    mm: int = 3,
    trend_window: int = 40,
    zscore_window: int = 126,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    deadband: float = 0.1,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Continuous-exposure-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = _exposure_dial(
        price_df, period, mm, trend_window, zscore_window, base_exposure, sensitivity, deadband, leverage_cap
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strategy_ret

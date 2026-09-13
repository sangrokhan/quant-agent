"""Strategy: SMA(short trend_window) trend-following gate with continuous
Aroon Oscillator sizing overlay -- SPY-focused trend-window recalibration
retrofit.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-086):
Direct follow-up applying the now four-times-validated shortened-trend-
window fix (RVI-082, CMO-083, Williams%R-084, %B-085 -- all converted a
QQQ-only accept into a dual QQQ+SPY accept by shortening trend_window from
200 to roughly 30-50) to Aroon Oscillator sizing (2026-09-13-072, previously
QQQ-only, SPY Sharpe near-miss 0.945 at trend_window=200). Same Aroon
sizing logic unchanged, only the SMA trend-confirmation window is swept
shorter. Own-data parameter-recalibration analysis (no new external source
this iteration -- continuing the systematic retrofit sweep).

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


def _aroon_oscillator(close: pd.Series, window: int) -> pd.Series:
    """Aroon Oscillator = AroonUp - AroonDown, range [-100, 100]."""
    def _periods_since_extreme(arr: np.ndarray, is_max: bool) -> np.ndarray:
        n = len(arr)
        out = np.full(n, np.nan)
        for end in range(window, n):
            seg = arr[end - window:end + 1]
            if np.any(np.isnan(seg)):
                continue
            idx = int(np.argmax(seg)) if is_max else int(np.argmin(seg))
            periods_since = window - idx
            out[end] = periods_since
        return out

    values = close.to_numpy(dtype=float)
    periods_since_high = _periods_since_extreme(values, is_max=True)
    periods_since_low = _periods_since_extreme(values, is_max=False)

    aroon_up = 100.0 * (window - periods_since_high) / window
    aroon_down = 100.0 * (window - periods_since_low) / window
    oscillator = aroon_up - aroon_down
    return pd.Series(oscillator, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    aroon_window: int = 25,
    aroon_reference: float = 60.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    oscillator = _aroon_oscillator(close, aroon_window)

    raw_exposure = (oscillator / aroon_reference).astype(float)
    exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap).fillna(0.0)

    position = exposure.where(trend_long.fillna(False), other=0.0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret

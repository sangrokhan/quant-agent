"""Strategy: Chande Forecast Oscillator (CFO) zero-line crossover, gated by
an ADX trend-strength filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-006):
The Chande Forecast Oscillator (Tushar Chande) measures the percentage gap
between the current close and the value of an OLS linear-regression line
fit through the trailing N closes: CFO = 100*(Close - RegressionValue(N))/
Close. Per arrowalgo.com's CFO guide, the recommended mechanical strategy is
a zero-line crossover (CFO crossing above 0 = price back above its own
recent linear trend, bullish) combined with an ADX(14)>25 trend-strength
filter, since the source explicitly warns that crossovers in isolation
"generate too many false signals... in choppy, ranging markets." Exit when
CFO crosses back below zero, ADX drops back below the threshold, or a
max_hold_days time-stop backstop. First Chande Forecast Oscillator strategy
in this repo -- distinct from the already-tested linear-regression-SLOPE
mean-reversion strategy (2026-09-04-058, trades the sign of the slope) and
linear-regression-channel BREAKOUT strategy (2026-09-04-141, trades
residual-band breaks), since CFO instead measures the pct deviation of
price from the regression line's own current value.

Signal logic
------------
- RegressionValue_t = OLS-fitted line value at the last point of a rolling
  cfo_window-bar window of closes (standard np.polyfit degree-1 fit).
- CFO_t = 100 * (close_t - RegressionValue_t) / close_t
- ADX(adx_period) computed via Wilder's standard DI+/DI-/DX smoothing.
- Entry (long): CFO crosses from <=0 to >0 AND ADX > adx_threshold.
- Exit: CFO crosses back below 0, OR ADX drops <= adx_threshold, OR a
  max_hold_days time-stop backstop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _linreg_value(close: pd.Series, cfo_window: int) -> pd.Series:
    x = np.arange(cfo_window, dtype=float)

    def _fit_last(window: np.ndarray) -> float:
        slope, intercept = np.polyfit(x, window, 1)
        return slope * (cfo_window - 1) + intercept

    return close.rolling(cfo_window).apply(_fit_last, raw=True)


def _chande_forecast_oscillator(close: pd.Series, cfo_window: int) -> pd.Series:
    reg_value = _linreg_value(close, cfo_window)
    cfo = 100.0 * (close - reg_value) / close
    return cfo


def _adx(df: pd.DataFrame, period: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr.replace(0.0, np.nan)
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr.replace(0.0, np.nan)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    cfo_window: int = 14,
    adx_period: int = 14,
    adx_threshold: float = 25.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cfo = _chande_forecast_oscillator(close, cfo_window)
    adx = _adx(df, adx_period)

    cfo_positive = cfo > 0
    entry_cross = cfo_positive & (~cfo_positive.shift(1).fillna(False))
    trend_ok = adx > adx_threshold

    entry = entry_cross & trend_ok.fillna(False)
    exit_signal = (~cfo_positive) | (~trend_ok.fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret

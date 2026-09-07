"""Strategy: Holt-Winters (double exponential smoothing) forecast-line
trend crossover with slope confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-063):
Per the TradingView "Holt-Winters Forecast Bands" indicator description
(https://www.tradingview.com/script/rcrVhyqk-Holt-Winters-Forecast-Bands/):
the Holt-Winters model tracks a LEVEL component (alpha-smoothed) and a
TREND component (beta-smoothed) recursively, producing a forecast line
that "provides a directional bias, helping traders anticipate whether the
price may continue along a trend or reverse" -- used here as a genuine
trend-following construction (the indicator explicitly recommends daily
timeframes for "swing trading and trend following").

Since daily QQQ/SPY/BTC/ETH bars have no fixed seasonal cycle (the
indicator's optional gamma/seasonality term assumes a repeating cycle
length, not applicable to non-seasonal financial series), this
implementation uses the two-parameter (level+trend) Holt linear-trend
model -- a direct, mechanically-defined simplification of the source's
three-parameter Holt-Winters, using only alpha/beta smoothing:
    level[t] = alpha*close[t] + (1-alpha)*(level[t-1]+trend[t-1])
    trend[t] = beta*(level[t]-level[t-1]) + (1-beta)*trend[t-1]
    forecast[t] = level[t] + trend[t]  (one-step-ahead projection)

Entry (long): close crosses above forecast[t-1] (price breaking above its
own smoothed forward-projected trend line) AND trend[t] > 0 (the model's
own trend component confirms upward slope -- the "directional bias" the
source describes). Exit: close crosses back below forecast[t-1], trend[t]
turns non-positive, or a max_hold_days time-stop.

First Holt-Winters/Holt double-exponential-smoothing forecast-based
strategy in this repo -- distinct from all prior single/double/triple EMA
variants (EMA, DEMA, TEMA, ZLEMA all just weighted moving averages with no
explicit recursive trend-component state) and from Kalman-filter trend
crossover (2026-09-08, single-state random-walk filter, no separate
trend-velocity state variable) -- Holt's method explicitly maintains and
compounds a distinct trend-velocity term into its one-step forecast,
which is a materially different recursive construction.

Source: https://www.tradingview.com/script/rcrVhyqk-Holt-Winters-Forecast-Bands/

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _holt_forecast(close: pd.Series, alpha: float, beta: float) -> tuple[np.ndarray, np.ndarray]:
    """Holt's linear-trend double exponential smoothing.

    Returns (forecast, trend) arrays, same length as close, with NaN for
    the initial warm-up bar (index 0).
    """
    c = close.to_numpy(dtype=float)
    n = len(c)
    level = np.full(n, np.nan)
    trend = np.full(n, np.nan)
    forecast = np.full(n, np.nan)

    if n < 2:
        return forecast, trend

    level[0] = c[0]
    trend[0] = 0.0
    for i in range(1, n):
        prev_level = level[i - 1]
        prev_trend = trend[i - 1]
        level[i] = alpha * c[i] + (1 - alpha) * (prev_level + prev_trend)
        trend[i] = beta * (level[i] - prev_level) + (1 - beta) * prev_trend
        forecast[i] = level[i] + trend[i]

    return forecast, trend


def generate_signals(
    price_df: pd.DataFrame,
    alpha: float = 0.2,
    beta: float = 0.1,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    forecast, trend = _holt_forecast(close, alpha, beta)
    c = close.to_numpy(dtype=float)

    # Cross above/below the PRIOR bar's forecast line (avoid same-bar
    # look-ahead: forecast[t] itself uses close[t]).
    prev_forecast = np.roll(forecast, 1)
    prev_forecast[0] = np.nan

    cross_above = (c > prev_forecast) & ~np.isnan(prev_forecast)
    cross_below = (c < prev_forecast) & ~np.isnan(prev_forecast)
    trend_positive = np.nan_to_num(trend, nan=0.0) > 0

    entry = cross_above & trend_positive
    exit_signal = cross_below | (~trend_positive)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal[i]) or held >= max_hold_days:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if bool(entry[i]):
                in_position = True
                entry_idx = i
                position[i] = 1
            else:
                position[i] = 0

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret

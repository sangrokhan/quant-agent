"""Strategy: Holt-Winters (double exponential smoothing) forecast-band
mean reversion -- fade price extensions outside adaptive volatility bands
back toward the Holt forecast baseline.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-137):
Per Google AI-overview synthesis of TradingView's "Holt-Winters Forecast
Bands" indicator description (https://www.tradingview.com/script/rcrVhyqk-Holt-Winters-Forecast-Bands/,
via browser_exec/google.com fallback -- web_search DDGS backend errors this
iteration): "A Holt-Winters mean reversion strategy uses the dynamic upper
and lower bands of the Holt-Winters Forecast Bands indicator as overbought
and oversold boundaries to fade extended price moves back toward the
central forecast line... Long Entry (Oversold): Open a buy order when the
price dips completely outside or touches the lower adaptive band... Exit
Rule: Close the trade when the price reverts and touches the central
forecast baseline."

This repo already tested the Holt-Winters forecast line as a TREND-FOLLOWING
crossover signal (2026-09-08-063, strategy file
2026-09-08_holt_winters_forecast_trend.py, accepted SPY-only) -- this
iteration is architecturally distinct: instead of trading breakouts through
the forecast line, this fades price extremes AWAY from adaptive bands built
around the same Holt forecast baseline, back toward it. Uses the identical
Holt linear-trend (level+trend, alpha/beta) recursive forecast construction
as its baseline, then adds an ATR-scaled adaptive band (source calls for
"adaptive volatility bands"; this repo has no free numeric band-width
multiplier disclosed, so ATR*band_mult is used, consistent with this repo's
convention for adaptive-band constructions elsewhere, e.g. Keltner/STARC).

Signal logic
------------
- Holt forecast[t] (level+trend recursive one-step-ahead projection, same
  construction as 2026-09-08-063).
- ATR(atr_period) scales the band width: upper = forecast + band_mult*ATR,
  lower = forecast - band_mult*ATR.
- Long entry: close crosses below (or touches) the lower band (oversold
  extension).
- Exit: close crosses back above the central forecast line (reversion
  complete, per source's own exit rule), OR a max_hold_days time-stop
  (this repo's standard safety exit since the source gives no time-stop).
- No short leg (long-only, consistent with this repo's other mean-reversion
  strategies).

Source: https://www.tradingview.com/script/rcrVhyqk-Holt-Winters-Forecast-Bands/
(indicator description synthesized via Google AI Overview)

Interface contract for validators/grid_test:
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


def _holt_forecast(close: pd.Series, alpha: float, beta: float):
    """Holt's linear-trend double exponential smoothing.

    Returns (forecast, trend) arrays, same length as close, with NaN for
    the initial warm-up bar (index 0). Identical construction to
    2026-09-08_holt_winters_forecast_trend.py.
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


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat(
        [
            (high - low),
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    alpha: float = 0.2,
    beta: float = 0.1,
    atr_period: int = 14,
    band_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    forecast, _trend = _holt_forecast(close, alpha, beta)
    atr = _atr(df, atr_period).to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)

    lower_band = forecast - band_mult * atr
    upper_band_baseline = forecast  # reversion target for the exit rule

    entry = (c <= lower_band) & ~np.isnan(lower_band)
    exit_signal = (c >= upper_band_baseline) & ~np.isnan(upper_band_baseline)

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
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

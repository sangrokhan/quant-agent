"""Strategy: SMA(trend_window) directional gate with continuous Coppock
Curve (WMA-smoothed dual-ROC composite momentum) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Coppock Curve (Edwin "Sedge" Coppock, 1962/1965): Curve = WMA(wma_window) of
[ROC(close, roc1_period) + ROC(close, roc2_period)], where ROC(n) =
(Close/Close.shift(n) - 1) * 100 and WMA applies linearly increasing weights
(1..wma_window) favoring recent values. Formula confirmed via Google
AI-overview synthesis of LightningChart/StockCharts ChartSchool/TradingView
(browser_exec fallback after web_search's DuckDuckGo backend returned "No
results found" this iteration). This repo has 14+ prior Coppock Curve
entries, ALL using it as a BINARY zero-line-crossover or trough/peak-turn
ENTRY trigger (one accepted QQQ-only via zero-cross, 2026-09-04-036). None
used Coppock's own continuous magnitude as a SIZING dial. This iteration
follows this cron trigger's repeatedly-validated continuous-sizing-dial
pattern (already zero-centered oscillators rolling z-scored + tanh-squashed
to [-1,1], used as a sizing multiplier within an SMA(trend_window) uptrend
gate, deadband to cut turnover, leverage_cap for crypto). First Coppock
Curve continuous-sizing variant in this repo.

Source: Google AI-overview synthesis (browser_exec fallback) of
LightningChart's Coppock Curve guide and StockCharts ChartSchool's
SharpCharts calculation definition (Coppock Curve = 10-period WMA of
14-period RoC + 11-period RoC), traditionally on monthly bars but reused at
daily-bar period counts here per this repo's established convention for
this indicator family (2026-09-04-036 and successors).

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


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = np.arange(1, window + 1, dtype=float)
    return series.rolling(window).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def _coppock_curve(
    close: pd.Series, roc1_period: int, roc2_period: int, wma_window: int
) -> pd.Series:
    roc1 = (close / close.shift(roc1_period) - 1.0) * 100.0
    roc2 = (close / close.shift(roc2_period) - 1.0) * 100.0
    composite = roc1 + roc2
    return _wma(composite, wma_window)


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
    roc1_period: int = 14,
    roc2_period: int = 11,
    wma_window: int = 10,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Coppock Curve (already zero-centered by construction) is rolling
    z-scored over `zscore_window` bars and tanh-squashed to [-1,+1] before
    use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    coppock = _coppock_curve(close, roc1_period, roc2_period, wma_window)

    roll_mean = coppock.rolling(zscore_window).mean()
    roll_std = coppock.rolling(zscore_window).std()
    zscore = (coppock - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    roc1_period: int = 14,
    roc2_period: int = 11,
    wma_window: int = 10,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        roc1_period=roc1_period,
        roc2_period=roc2_period,
        wma_window=wma_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

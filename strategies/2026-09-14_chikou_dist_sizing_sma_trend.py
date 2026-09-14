"""Strategy: SMA(trend_window) directional gate with continuous Chikou
Span (Ichimoku lagging line) normalized-distance sizing overlay +
deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Chikou Span (Ichimoku "lagging span"), per Investopedia/TrueData (browser_exec
fallback since web_search's DDG backend TLS-errored this query): the current
period's closing price, conventionally plotted `displacement` (default 26)
periods back on the chart to visually compare "now" against price action
`displacement` bars ago. Its standard qualitative interpretation is
sentiment confirmation: Chikou (i.e. today's close) above the close from
`displacement` bars ago = bullish confirmation, below = bearish. Repo has
1 prior Chikou Span mention (2026-09-05-085), used only as a 3rd AND-gate
condition inside a full Ichimoku confluence system, never isolated or used
continuously. This iteration isolates Chikou's own construction as a
standalone CONTINUOUS SIZING dial: the normalized distance
(Close_t - Close_{t-displacement}) / Close_{t-displacement}, rolling
z-scored + tanh-squashed to [-1,1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate, deadband to cut turnover, leverage_cap for
crypto. First standalone Chikou Span continuous-sizing variant.

Source: https://www.investopedia.com/terms/i/ichimokuchart.asp (Chikou Span
definition), cross-referenced with https://www.truedata.in/ichimoku-cloud-indicator
(formula confirmation) via browser_exec Google SERP snippets.

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
    displacement: int = 26,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Chikou Span's own construction -- current close vs close `displacement`
    bars ago, normalized -- is rolling-z-scored over `zscore_window` bars
    and tanh-squashed to [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    close_lagged = close.shift(displacement)
    chikou_dist = (close - close_lagged) / close_lagged.replace(0.0, np.nan)

    roll_mean = chikou_dist.rolling(zscore_window).mean()
    roll_std = chikou_dist.rolling(zscore_window).std()
    zscore = (chikou_dist - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    displacement: int = 26,
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
        displacement=displacement,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

"""Strategy: Heikin Ashi Smoothed distance/momentum as a CONTINUOUS SIZING
dial within an SMA(trend_window) uptrend gate, leverage-cap-aware for
crypto.

Hypothesis (this cron trigger, iteration 8):
This repo has 2 prior "Dual Heiken Ashi Smoothed" entries (2026-09-09-062,
-063), both BINARY fast/slow crossover triggers (rejected: full-sample
Sharpe fail, edge concentrated in low-vol tercile, a vol-regime gate fix
made results worse rather than better). Per the Barchart/MQL5/ForexFactory
research synthesis (read this iteration): "Heikin Ashi Smoothed" applies a
moving-average smoothing pass to raw OHLC BEFORE computing standard
Heikin-Ashi candles (HA_close = mean(O,H,L,C) of the SMOOTHED bar;
HA_open/high/low derived recursively as in classic HA), producing a
less-noisy trend proxy than raw HA. This iteration follows this repo's
established binary-to-continuous-sizing-dial rescue pattern (successful for
DPO, Hurst, VHF, TII, RVI, Kalman slope, CBOE SKEW, Ichimoku Kumo-distance,
VPT-ROC, Pivot Point SuperTrend, etc.): rather than a fast/slow HA-color
crossover trigger, this iteration uses the smoothed-HA candle body's own
normalized strength (HA_close - HA_open, scaled by the raw close's rolling
ATR) as a rolling z-scored, tanh-squashed continuous exposure dial, applied
within an SMA(trend_window) uptrend gate with a deadband. Distinct
construction from both prior binary Dual-HA-Smoothed entries (single
smoothed-HA series' own candle-body strength, not a fast/slow crossover of
two separately-smoothed HA series).

Source: Barchart Technical Indicators glossary (Heikin-Ashi Smoothed
listing), MQL5/ForexFactory corroboration of the smoothing-before-HA
construction (read via browser_exec this iteration -- web_search's
DuckDuckGo backend intermittently failing with TLS errors this run).

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


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr


def _smoothed_heikin_ashi(
    open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series,
    smooth_period: int,
) -> tuple[pd.Series, pd.Series]:
    """Apply EMA smoothing to raw OHLC first, then compute standard
    Heikin-Ashi candles on the smoothed series. Returns (ha_open, ha_close).
    """
    s_open = open_.ewm(span=smooth_period, adjust=False).mean()
    s_high = high.ewm(span=smooth_period, adjust=False).mean()
    s_low = low.ewm(span=smooth_period, adjust=False).mean()
    s_close = close.ewm(span=smooth_period, adjust=False).mean()

    n = len(s_close)
    ha_close = (s_open + s_high + s_low + s_close) / 4.0
    ha_open = np.zeros(n)
    so = s_open.to_numpy()
    hc = ha_close.to_numpy()
    for i in range(n):
        if i == 0:
            ha_open[i] = so[i]
        else:
            ha_open[i] = (ha_open[i - 1] + hc[i - 1]) / 2.0
    return pd.Series(ha_open, index=close.index), ha_close


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    smooth_period: int = 10,
    atr_period: int = 14,
    zscore_window: int = 126,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    dial = tanh(zscore((HA_close - HA_open)/ATR, zscore_window)) -- a
    stronger smoothed-HA bullish candle body (relative to ATR) pushes the
    dial positive (increase exposure); a bearish body pushes it negative
    (reduce exposure), gated to 0 whenever close is below its
    SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    trend_long = close > close.rolling(trend_window).mean()

    ha_open, ha_close = _smoothed_heikin_ashi(open_, high, low, close, smooth_period)
    tr = _true_range(high, low, close)
    atr = tr.rolling(atr_period).mean()

    body = (ha_close - ha_open) / atr.replace(0.0, np.nan)

    roll_mean = body.rolling(zscore_window).mean()
    roll_std = body.rolling(zscore_window).std(ddof=0)
    z = (body - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(z.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    smooth_period: int = 10,
    atr_period: int = 14,
    zscore_window: int = 126,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        smooth_period=smooth_period,
        atr_period=atr_period,
        zscore_window=zscore_window,
        sensitivity=sensitivity,
        base_exposure=base_exposure,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

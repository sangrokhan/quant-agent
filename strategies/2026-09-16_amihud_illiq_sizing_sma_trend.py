"""Strategy: SMA(trend_window) directional gate with continuous Amihud
illiquidity-z-score sizing overlay (inverse relationship: exposure shrinks
as illiquidity spikes) + deadband, leverage-cap-aware for crypto from the
start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per Amihud (2002) and https://microalphas.com/amihud-illiquidity/ (read via
browser_exec fallback this iteration -- web_search's DDGS backend errored
with a TLS RequestError on the direct sizing-oriented query, and
web_extract's configured backend is search-only/cannot extract page
content, so browser_exec drove both the Google SERP discovery and the page
read): ILLIQ = mean(|daily return| / dollar_volume) over a rolling window
measures price impact per dollar traded -- a high value means the market
could not absorb trading flow without repricing (illiquid/stressed), a low
value means deep/liquid conditions. The source's own "Using Amihud as a
Signal" section explicitly describes "liquidity timing": treat sharp
increases in aggregate/security ILLIQ as a risk signal, since "rising
illiquidity has historically accompanied stress and drawdowns."

This repo already tested Amihud ILLIQ once (id 2026-09-05-027,
strategies/2026-09-05_amihud_illiquidity_regime_filter.py): a BINARY
risk-off/long threshold gate at z-score>=2.0, accepted equity-only (QQQ,
SPY), decisively rejected crypto (0/54 grid cells), with notes flagging the
counter-intuitive finding that the edge was strongest in LOW-vol regimes
and degraded in high-vol -- suggesting the hard binary cutoff at z=2.0 may
be discarding useful information in the continuum below/above that
threshold. This iteration reframes the identical, already-confirmed Amihud
ILLIQ formula as a CONTINUOUS SIZING dial (exposure inversely scales with
the illiquidity z-score, tanh-squashed, no hard cutoff) within an
SMA(trend_window) uptrend gate -- the same continuous-sizing-dial pattern
that has rescued numerous other binary-trigger rejections/narrow-accepts
this repo has tried on other indicator families (Vortex, TSI, RMI, SMI,
BOP, Mass Index, GMMA, Trend Magic, etc.), applied here for the first time
to a liquidity/microstructure-proxy indicator rather than a momentum/
trend oscillator. First Amihud-as-continuous-sizing-dial strategy in this
repo -- distinct from 2026-09-05-027's binary gate.

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


def _amihud_illiq_zscore(
    close: pd.Series,
    volume: pd.Series,
    illiq_window: int,
    zscore_window: int,
) -> pd.Series:
    """Rolling Amihud ILLIQ, z-scored vs its own trailing history.

    Positive z = illiquidity spiking above its recent norm (stress-like);
    negative z = unusually deep/liquid conditions.
    """
    daily_ret = close.pct_change()
    dollar_volume = (close * volume).replace(0, np.nan)
    daily_illiq = (daily_ret.abs() / dollar_volume) * 1_000_000
    rolling_illiq = daily_illiq.rolling(illiq_window, min_periods=illiq_window).mean()

    roll_mean = rolling_illiq.rolling(zscore_window, min_periods=illiq_window).mean()
    roll_std = rolling_illiq.rolling(zscore_window, min_periods=illiq_window).std()
    zscore = (rolling_illiq - roll_mean) / roll_std.replace(0.0, np.nan)
    return zscore


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
    illiq_window: int = 20,
    zscore_window: int = 252,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    exposure = clip(base_exposure - sensitivity * tanh(illiq_zscore), 0, cap)
    gated to 0 whenever close is below its SMA(trend_window) (uptrend gate).
    Illiquidity spikes (positive z) shrink exposure; unusually liquid/calm
    conditions (negative z) expand it toward leverage_cap.
    """
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    trend_long = close > close.rolling(trend_window).mean()
    zscore = _amihud_illiq_zscore(close, volume, illiq_window, zscore_window)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure - sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)
    raw_exposure = raw_exposure.where(~zscore.isna(), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    illiq_window: int = 20,
    zscore_window: int = 252,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        illiq_window=illiq_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

"""Strategy: SMA(trend_window) directional gate with continuous SVE
(Vervoort Volatility) Bands %b-style sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Sylvain Vervoort's SVE / Volatility Bands (per LuxAlgo's "SVE Bands"
description, browser_exec fallback since traders.com's original TASC
article is Cloudflare-gated and web_search DDG backend errored on
multiple queries this iteration): typical price is double exponentially
smoothed to build a low-flicker centerline, and the bands offset that
centerline by an exponentially averaged range-flavored deviation measure
(so single erratic bars barely move the bands). Default settings per
LuxAlgo: smoothing_length=8 (double EMA pass), volatility_length=13,
deviation_mult=3.55 (upper), lower_band_adjust=0.9 (asymmetric lower band).
Repo has 1 prior Vervoort Volatility Band entry (2026-09-08-022, a
rejected 3-candle discrete reversal-pattern trigger). This iteration
reframes the indicator's own %b-style position (Close's normalized
location within the [lower, upper] band) as a CONTINUOUS SIZING dial:
rolling z-scored + tanh-squashed to [-1,1], used as a sizing multiplier
within an SMA(trend_window) uptrend gate, deadband to cut turnover,
leverage_cap for crypto. First Vervoort Volatility Band continuous-sizing
variant.

Source: https://www.luxalgo.com/library/indicator/zXEjsttC-vervoort-volatility-bands/
("SVE Bands" description page -- exact double-smoothing/deviation-mult/
lower-adjust parameterization); TradingView LazyBear port page confirmed
existence/attribution but redirected to the same Cloudflare-gated TASC
source for the raw formula, so the LuxAlgo parameterization is used as the
primary numeric source this iteration.

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


def _sve_bands(
    high: pd.Series, low: pd.Series, close: pd.Series,
    smoothing_length: int, volatility_length: int,
    deviation_mult: float, lower_band_adjust: float,
):
    typical = (high + low + close) / 3.0
    smooth1 = typical.ewm(span=smoothing_length, adjust=False).mean()
    centerline = smooth1.ewm(span=smoothing_length, adjust=False).mean()  # double pass

    # Range-flavored deviation measure (true-range style), smoothed.
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    deviation = tr.ewm(span=volatility_length, adjust=False).mean()

    upper = centerline + deviation_mult * deviation
    lower = centerline - lower_band_adjust * deviation_mult * deviation
    return centerline, upper, lower


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
    smoothing_length: int = 8,
    volatility_length: int = 13,
    deviation_mult: float = 3.55,
    lower_band_adjust: float = 0.9,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    SVE %b (normalized Close position within [lower, upper] band, centered
    to [-1,+1] as 2*%b-1) is rolling-z-scored over `zscore_window` bars and
    tanh-squashed to [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    trend_long = close > close.rolling(trend_window).mean()
    _, upper, lower = _sve_bands(
        high, low, close, smoothing_length, volatility_length,
        deviation_mult, lower_band_adjust,
    )

    band_width = (upper - lower).replace(0.0, np.nan)
    pctb = (close - lower) / band_width
    centered_pctb = 2.0 * pctb - 1.0

    roll_mean = centered_pctb.rolling(zscore_window).mean()
    roll_std = centered_pctb.rolling(zscore_window).std()
    zscore = (centered_pctb - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    smoothing_length: int = 8,
    volatility_length: int = 13,
    deviation_mult: float = 3.55,
    lower_band_adjust: float = 0.9,
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
        smoothing_length=smoothing_length,
        volatility_length=volatility_length,
        deviation_mult=deviation_mult,
        lower_band_adjust=lower_band_adjust,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

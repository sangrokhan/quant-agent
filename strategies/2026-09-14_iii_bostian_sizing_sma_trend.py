"""Strategy: SMA(trend_window) directional gate with continuous Intraday
Intensity Index (III, David Bostian) volume-pressure sizing overlay +
deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Intraday Intensity Index (III, David Bostian): III = ((Close*2 - High -
Low) / (High - Low)) * Volume -- a volume-weighted measure of where the
close falls within the day's high-low range, per bar. Per Investopedia
(https://www.investopedia.com/terms/i/intradayintensityindex.asp, visited
this iteration via browser_exec after web_search's DDGS backend hit a TLS
RequestError -- normal fallback, not a page-specific failure): "when the
intraday highs and lows move above the closing price with volume, the
index moves sharply negative" (distribution pressure); the opposite
(strong close near the day's high on high volume) is accumulation
pressure. First Intraday Intensity Index / Bostian strategy in this repo.

III itself is a raw unbounded per-bar volume-weighted quantity (structurally
similar to Chaikin Money Flow's close-location-value * volume numerator,
but WITHOUT CMF's rolling-sum-ratio normalization step). This iteration
normalizes it the way Chaikin Money Flow does -- a rolling N-bar sum of
III divided by the rolling N-bar sum of volume -- which naturally bounds
the result roughly in [-1, +1] (since the CLV term itself is bounded
[-1,+1] and this is a volume-weighted average of it), then uses that
bounded "smoothed III ratio" directly as a continuous sizing dial within
the existing SMA(trend_window) uptrend gate used by this cron trigger's
other sizing-dial strategies.

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


def _iii_ratio(high: pd.Series, low: pd.Series, close: pd.Series,
               volume: pd.Series, smooth_window: int = 21) -> pd.Series:
    """Chaikin-style normalized Intraday Intensity: rolling N-bar sum of
    raw III divided by rolling N-bar sum of volume, bounded ~[-1, +1].

    Raw III = ((close*2 - high - low) / (high - low)) * volume.
    """
    hl_range = (high - low).replace(0, np.nan)
    raw_iii = ((close * 2.0 - high - low) / hl_range) * volume
    num = raw_iii.rolling(smooth_window).sum()
    denom = volume.rolling(smooth_window).sum().replace(0, np.nan)
    return (num / denom).clip(lower=-1.0, upper=1.0)


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
    smooth_window: int = 21,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Smoothed III ratio is bounded ~[-1,+1] by construction (Chaikin-style
    rolling-sum normalization) -- no additional min-max/z-score needed.
    Exposure = base_exposure + sensitivity * smoothed_iii_ratio, clipped to
    [0, leverage_cap], gated to zero outside the SMA(trend_window) uptrend.
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)

    trend_long = close > close.rolling(trend_window).mean()
    iii_ratio = _iii_ratio(high, low, close, volume, smooth_window)

    raw_exposure = base_exposure + sensitivity * iii_ratio
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    smooth_window: int = 21,
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
        smooth_window=smooth_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

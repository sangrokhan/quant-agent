"""Strategy: SMA(trend_window) directional gate with continuous
Heikin-Ashi-close-vs-TEMA distance (HACOLT-inspired, Sylvain Vervoort)
sizing overlay + deadband, leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-15-037, this cron trigger):
Vervoort's HACOLT (Heikin-Ashi Candles Oscillator Long Term), per
https://www.tradingview.com/script/4zuhGaAU-Vervoort-Heiken-Ashi-LongTerm-Candlestick-Oscillator-HACOLT/
and Google's AI-overview summary (both visited this iteration): smooths
modified Heikin-Ashi close prices with a zero-lag TEMA (default period 55)
and produces a discrete 3-level state (-1/0/1: open-short/no-position/
open-long), transitioning on rises/falls through those levels.

Distinct from this repo's several existing plain-Heikin-Ashi entries
(which all use candle color/consecutive-count/crossover rules on the raw
HA candles) -- this construction specifically smooths the HA *close* with
a TEMA (triple exponential moving average, zero-lag cascaded-EMA
construction) before generating a signal, a materially different
mechanism. The exact HACO sub-formula and 3-level state machine wasn't
fully extractable from the sources this iteration (TradingView source-code
view was blocked), so rather than replicate the discrete 3-level state
machine, this reuses the cron trigger's established continuous-sizing-dial
pattern: the Heikin-Ashi close's percentage distance from its own TEMA
smoothing is rolling z-scored and tanh-squashed into [-1,+1] as an exposure
multiplier inside an SMA(trend_window) uptrend gate with a deadband.

Heikin-Ashi close is used (rather than raw close) specifically because
Vervoort's own construction argues the HA-smoothed price series is a
cleaner trend proxy than raw OHLC, and TEMA (vs SMA/EMA) is used
specifically for its explicitly reduced-lag design intent.

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


def _heikin_ashi_close(df: pd.DataFrame) -> pd.Series:
    open_ = df["open"] if "open" in df.columns else df["close"]
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    ha_close = (open_ + high + low + close) / 4.0
    return ha_close


def _tema(series: pd.Series, period: int) -> pd.Series:
    ema1 = series.ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    ema3 = ema2.ewm(span=period, adjust=False).mean()
    return 3.0 * ema1 - 3.0 * ema2 + ema3


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
    tema_period: int = 55,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Heikin-Ashi close's percentage distance from its own TEMA(tema_period)
    is rolling z-scored over `zscore_window` and tanh-squashed to [-1,+1]
    before use as a sizing dial, gated by an SMA(trend_window) uptrend
    filter on the raw close.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    ha_close = _heikin_ashi_close(df)
    tema = _tema(ha_close, tema_period)
    pct_dist = (ha_close - tema) / tema.replace(0.0, np.nan)

    roll_mean = pct_dist.rolling(zscore_window).mean()
    roll_std = pct_dist.rolling(zscore_window).std()
    zscore = (pct_dist - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    tema_period: int = 55,
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
        tema_period=tema_period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

"""Strategy: SMA(trend_window) directional gate with continuous "exhaustion
distance" sizing overlay + deadband, adapted from Perry J. Kaufman's "An Ag
Selling Model" (TASC August 2026 Traders' Tips, thinkorswim implementation),
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Kaufman's Ag Selling Model (per
https://traders.com/documentation/feedbk_docs/2026/08/traderstips.html,
visited this iteration -- web_search DDGS backend failing with
RequestError/TLS-close-notify on every query, browser_exec fallback used for
the whole iteration) triggers a SELL/short-entry for soybean futures whenever
price extends above a "sell level" = SMA(averageLength) + ATR(atrLength) *
atrFactor, i.e. it treats extension of price materially above a rolling
trend+ATR band as an exhaustion/overbought signal warranting reduced
long exposure (in the original: outright short entry, since it's a
commodity-producer hedging model with a crop-year cycle irrelevant to
equities/crypto). This repo has one prior use of an SMA+ATR band
(2026-09-09-096, ATR Channel Breakout) but that used the band as a
BREAKOUT-CONTINUATION entry trigger (long when price breaks ABOVE the band,
i.e. treating extension as bullish momentum) -- the opposite economic
interpretation from Kaufman's exhaustion/mean-reversion framing. This
strategy reframes Kaufman's "sell level" distance as a CONTINUOUS SIZING
dial that FADES (reduces) long exposure the further price extends above the
band, inside an SMA(trend_window) uptrend gate with deadband -- testing
whether the exhaustion interpretation (reduce into strength) beats or
complements the momentum interpretation already tested. First
exhaustion-fade-band-distance-as-continuous-sizing-dial strategy in this
repo; first indicator-family use of "Ag Selling Model" logic outside
commodities.

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


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


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
    average_length: int = 40,
    atr_length: int = 20,
    atr_factor: float = 2.5,
    base_exposure: float = 0.75,
    sensitivity: float = 1.0,
    leverage_cap: float = 1.0,
    deadband: float = 0.35,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    "Sell level" = SMA(average_length) + ATR(atr_length) * atr_factor, per
    Kaufman's Ag Selling Model. Distance = (close - sell_level) / ATR,
    clipped at 0 on the downside (no bonus exposure for being far below the
    band -- only a fade effect once price extends above it). Exposure
    dial = base_exposure - sensitivity * clip(distance, 0, 3) / 3, i.e.
    linearly fades from base_exposure toward 0 as price extends from 0 to 3x
    ATR above the sell level. Applied only within an SMA(trend_window)
    uptrend gate (long-only system; the original's short-entry is not
    replicated per SAFETY.md's long-only backtest scope for this repo's
    sizing-dial family).
    """
    df = _prep(price_df)
    close, high, low = df["close"], df["high"], df["low"]

    trend_long = close > close.rolling(trend_window).mean()

    sma = close.rolling(average_length).mean()
    tr = _true_range(high, low, close)
    atr = tr.rolling(atr_length).mean()
    sell_level = sma + atr * atr_factor

    distance = (close - sell_level) / atr.replace(0.0, np.nan)
    distance = distance.clip(lower=0.0, upper=3.0).fillna(0.0)

    dial = distance / 3.0  # 0 (at/below sell level) .. 1 (far extended)
    raw_exposure = base_exposure - sensitivity * base_exposure * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    average_length: int = 40,
    atr_length: int = 20,
    atr_factor: float = 2.5,
    base_exposure: float = 0.75,
    sensitivity: float = 1.0,
    leverage_cap: float = 1.0,
    deadband: float = 0.35,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        average_length=average_length,
        atr_length=atr_length,
        atr_factor=atr_factor,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

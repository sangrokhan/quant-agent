"""Strategy: SMA(trend_window) directional gate with continuous Elder
AutoEnvelope (Dr. Alexander Elder) position-in-channel sizing overlay +
deadband, leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-16-048, this cron trigger):
Elder AutoEnvelope, per Dr. Alexander Elder's own description (corroborated
by TradingView/Scribd/Worden-D summaries, visited this iteration via
browser_exec Google fallback -- web_search DDGS backend failed with a TLS
RequestError for the earlier "Vervoort" query in this same iteration, so the
research angle was redirected to this candidate): a 13-day EMA is the
"market consensus of value"; an upper envelope is plotted above the EMA and
a lower envelope below it, each offset by a volatility-derived amount
(operationalized here as an ATR(atr_window) multiple, since Elder's own
"Auto" feature ties the channel width to recent volatility rather than a
fixed percentage). Elder's own trading rule combines the envelope extremes
with a trend filter (Elder Impulse/Elder-Ray) so overbought/oversold signals
are only acted on in the direction of the dominant trend -- reused here as
the pre-existing SMA(trend_window) uptrend gate already established in this
repo's sizing-dial pattern. First Elder-AutoEnvelope-specific strategy in
this repo (distinct from the already-tested plain MA Envelope,
fixed-percentage construction with no ATR/volatility adaptation, and from
Elder Ray/Elder Impulse/Elder Force Index/Elder SafeZone which are separate
indicators from the same author).

Construction (continuous sizing dial, following this repo's established
position-within-a-channel pattern, e.g. STARC/%B/Keltner-%B): position of
close within the ATR-scaled envelope around the 13-day EMA
(pos = (close - ema) / (atr_mult * ATR)), clipped to [-1,+1], is used
directly (no separate z-score needed since it is already naturally bounded)
as a continuous sizing dial -- close pinned near/above the upper envelope
(overbought, but per Elder only actionable long when the broader trend is
already up) scales exposure up, close near/below the lower envelope scales
exposure down -- inside an SMA(trend_window) uptrend gate with a deadband
to cut turnover.

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


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    prior_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prior_close).abs(),
            (low - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


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
    ema_window: int = 13,
    atr_window: int = 20,
    atr_mult: float = 2.0,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Elder AutoEnvelope: 13-day EMA (`ema_window`) with an ATR-scaled
    envelope (`atr_window`, `atr_mult`). Close's position within the
    envelope, clipped to [-1,+1], is used directly as a sizing dial, gated
    by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    ema = close.ewm(span=ema_window, adjust=False).mean()
    atr = _atr(high, low, close, atr_window)
    envelope_width = (atr_mult * atr).replace(0.0, np.nan)

    dial = ((close - ema) / envelope_width).clip(lower=-1.0, upper=1.0).fillna(0.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ema_window: int = 13,
    atr_window: int = 20,
    atr_mult: float = 2.0,
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
        ema_window=ema_window,
        atr_window=atr_window,
        atr_mult=atr_mult,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

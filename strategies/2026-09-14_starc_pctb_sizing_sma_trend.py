"""Strategy: SMA(trend_window) directional gate with continuous STARC %B
sizing overlay + deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
STARC Bands (Stoller Average Range Channels, Manning Stoller): Upper = SMA(n)
+ K*ATR(n), Lower = SMA(n) - K*ATR(n) -- an ATR-based (not std-dev-based)
volatility envelope. Per LightningChart
(https://lightningchart.com/blog/en/starc-bands-stoller-average-range-channel-for-trading/,
visited this iteration via browser_exec after web_search's DuckDuckGo
backend returned no usable text result for the query).

This repo has 2 prior STARC entries (2026-09-04-146 lower-band-touch entry
gated by uptrend SMA, and 2026-09-06-141 lower-band-touch 3-bar reversal
pattern), both REJECTED, both binary band-touch triggers. This iteration
reframes STARC as a Bollinger-%B-style CONTINUOUS SIZING dial:
    starc_pctb = (close - lower) / (upper - lower)
which is naturally centered ~0.5 inside the band and can exceed [0,1] when
price pierces a band, rescaled here via (starc_pctb - 0.5) * 2 to a
zero-centered dial, clipped to [-1,+1], then used as a sizing multiplier
within an SMA(trend_window) uptrend gate -- following this cron trigger's
validated continuous-sizing-dial pattern (STARC %B has not previously been
tested this way in this repo; distinct from the Bollinger-Band %B family
already tested since STARC's envelope width is ATR-based, not std-dev-based).

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


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _starc_pctb(df: pd.DataFrame, sma_window: int, atr_window: int, k: float) -> pd.Series:
    """STARC %B: (close - lower) / (upper - lower), Upper/Lower = SMA +/- K*ATR.

    Naturally centered ~0.5 within the band; can exceed [0,1] on band pierces.
    """
    close = df["close"]
    sma = close.rolling(sma_window).mean()
    atr = _atr(df, atr_window)
    upper = sma + k * atr
    lower = sma - k * atr
    band_width = (upper - lower).replace(0.0, np.nan)
    pctb = (close - lower) / band_width
    return pctb


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
    starc_sma_window: int = 20,
    starc_atr_window: int = 15,
    starc_k: float = 1.5,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    STARC %B is centered ~0.5; rescaled to a zero-centered dial via
    (pctb - 0.5) * 2, clipped to [-1, 1], then used as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pctb = _starc_pctb(df, starc_sma_window, starc_atr_window, starc_k)
    pctb_centered = ((pctb - 0.5) * 2.0).clip(-1.0, 1.0)

    raw_exposure = base_exposure + sensitivity * pctb_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    starc_sma_window: int = 20,
    starc_atr_window: int = 15,
    starc_k: float = 1.5,
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
        starc_sma_window=starc_sma_window,
        starc_atr_window=starc_atr_window,
        starc_k=starc_k,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

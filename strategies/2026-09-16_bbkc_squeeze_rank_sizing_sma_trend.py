"""Strategy: SMA(trend_window) directional gate with continuous BB/KC
Squeeze Percent-Rank sizing overlay + deadband, leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-16-052, this cron trigger):
Volatility Squeeze Percent Rank, per Google AI-overview (TradingView
corroborating, visited this iteration via browser_exec Google fallback):
instead of the standard discrete Boolean squeeze test (is Bollinger Band
Width < Keltner Channel Width), compute the ratio R = BBW/KCW on every bar
(BBW = Bollinger upper-lower, KCW = Keltner upper-lower, both around a
shared basis) and take its rolling percentile rank over a lookback window.
This yields a smooth 0-100% scale of "how tight volatility is right now
relative to its own recent history" rather than a binary squeeze/no-squeeze
flag. Distinct from this repo's existing BBW-only continuous-sizing dial
(id 2026-09-14-150, min-max normalized single-band-width) since this
construction (a) compares TWO bands (Bollinger vs Keltner) rather than one
band's width in isolation, and (b) uses a percentile-RANK transform (order
statistic, inherently robust to distributional shifts) rather than min-max
normalization (sensitive to sample extremes). First BB/KC-ratio-based
sizing dial in this repo.

Construction (continuous sizing dial): rolling percentile rank of R =
BBW/KCW over `rank_window` bars, inverted (1 - rank) so that tight
volatility (low ratio, historically compressed) scales exposure UP (same
inverse-volatility-conditioning intuition already validated in this repo
via GAPO/BBW: pre-breakout compression favors leaning in), used as a
continuous exposure-sizing dial inside an SMA(trend_window) uptrend gate
with a deadband.

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


def _squeeze_ratio(
    high: pd.Series, low: pd.Series, close: pd.Series,
    bb_window: int, bb_std: float, kc_window: int, kc_mult: float,
) -> pd.Series:
    """R = Bollinger Band Width / Keltner Channel Width."""
    basis = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    bbw = 2.0 * bb_std * std

    ema = close.ewm(span=kc_window, adjust=False).mean()
    atr = _atr(high, low, close, kc_window)
    kcw = 2.0 * kc_mult * atr

    ratio = bbw / kcw.replace(0.0, np.nan)
    return ratio


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
    bb_window: int = 20,
    bb_std: float = 2.0,
    kc_window: int = 20,
    kc_mult: float = 1.5,
    rank_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Rolling percentile rank of the BB/KC width ratio over `rank_window` is
    inverted so compression scales exposure up, used as a sizing dial
    gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    ratio = _squeeze_ratio(high, low, close, bb_window, bb_std, kc_window, kc_mult)

    pct_rank = ratio.rolling(rank_window).apply(
        lambda x: (x < x[-1]).sum() / len(x), raw=True
    )
    dial = (1.0 - 2.0 * pct_rank).fillna(0.0)  # compression (low rank) -> +1

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    bb_window: int = 20,
    bb_std: float = 2.0,
    kc_window: int = 20,
    kc_mult: float = 1.5,
    rank_window: int = 100,
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
        bb_window=bb_window,
        bb_std=bb_std,
        kc_window=kc_window,
        kc_mult=kc_mult,
        rank_window=rank_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

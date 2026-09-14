"""Strategy: SMA(trend_window) directional gate with continuous Chande
Kroll Stop (CKSP) normalized-distance sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Chande Kroll Stop (Tushar Chande & Stanley Kroll, 1994), per prior repo
entries citing LuxAlgo/trendspider.com formula:
    first_high_stop = Highest(High, p) - atr_mult * ATR(p)
    first_low_stop  = Lowest(Low, p)  + atr_mult * ATR(p)
    stop_long  = Highest(first_high_stop, q)   (upper/short-side stop line)
    stop_short = Lowest(first_low_stop, q)     (lower/long-side stop line)
This repo has 3 prior Chande Kroll Stop entries (2026-09-04-116, -149,
2026-09-10-063), all binary dual-line breakout triggers (long when close
crosses above BOTH lines), none accepted. This iteration reframes the
indicator's own midline-distance -- normalized position of Close relative
to the [stop_short, stop_long] band, (Close - mid) / (stop_long -
stop_short) where mid = (stop_long + stop_short) / 2 -- as a CONTINUOUS
SIZING dial: rolling z-scored + tanh-squashed to [-1,1], used as a sizing
multiplier within an SMA(trend_window) uptrend gate, deadband to cut
turnover, leverage_cap for crypto. First Chande Kroll Stop continuous-sizing
variant.

Source: prior repo research (LuxAlgo / trendspider.com Chande Kroll Stop
formula, already vetted in 2026-09-10-063); this iteration reuses the
confirmed formula and only changes how the indicator's output is consumed
(continuous sizing dial instead of a discrete breakout trigger).

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
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _cksp_lines(
    high: pd.Series, low: pd.Series, close: pd.Series,
    p: int, atr_mult: float, q: int,
):
    atr = _atr(high, low, close, p)
    first_high_stop = high.rolling(p).max() - atr_mult * atr
    first_low_stop = low.rolling(p).min() + atr_mult * atr
    stop_long = first_high_stop.rolling(q).max()
    stop_short = first_low_stop.rolling(q).min()
    return stop_long, stop_short


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
    p: int = 10,
    atr_mult: float = 1.0,
    q: int = 9,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    CKSP's normalized position of Close within the [stop_short, stop_long]
    band -- (Close - mid) / (stop_long - stop_short) -- is rolling-z-scored
    over `zscore_window` bars and tanh-squashed to [-1,+1] before use as a
    sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    trend_long = close > close.rolling(trend_window).mean()
    stop_long, stop_short = _cksp_lines(high, low, close, p, atr_mult, q)

    band_width = (stop_long - stop_short).replace(0.0, np.nan)
    mid = (stop_long + stop_short) / 2.0
    norm_dist = (close - mid) / band_width

    roll_mean = norm_dist.rolling(zscore_window).mean()
    roll_std = norm_dist.rolling(zscore_window).std()
    zscore = (norm_dist - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    p: int = 10,
    atr_mult: float = 1.0,
    q: int = 9,
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
        p=p,
        atr_mult=atr_mult,
        q=q,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

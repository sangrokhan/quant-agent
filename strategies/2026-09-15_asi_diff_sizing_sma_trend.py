"""Strategy: SMA(trend_window) directional gate with continuous Wilder
Accumulative Swing Index (ASI) sizing overlay + deadband, leverage-cap-aware
for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Wilder's Swing Index (SI), per FXOpen's ASI explainer:
  SI = 50 * (C - CP + 0.5*(CP - OP) + 0.25*(C - O)) / R
  where C=close, CP=prev close, O=open, OP=prev open,
  R = max(High-C, Low-C, High-CP, Low-CP) (absolute value).
  ASI_t = ASI_{t-1} + SI_t  (running cumulative sum).
Source: https://fxopen.com/blog/en/accumulative-swing-index-definition-and-how-to-use-it/
(full SI/ASI formula, confirmed via browser_exec after web_search's DDGS
backend returned no results for this query).

Repo has 3 prior ASI entries, all discrete-trigger constructions: a
zero-line-cross (decisive reject, 0/216 grid cells), a swing-channel
breakout on the ASI line itself (persistent near-miss, Sharpe 0.734
SPY/0.949 QQQ), and that same breakout with a vol-regime gate added
(still a persistent near-miss, Sharpe 0.781 QQQ/0.843 SPY -- every other
validator passed cleanly both times, only Sharpe fell short). None tried
a CONTINUOUS SIZING dial. This iteration reframes ASI's deviation from its
own EMA (a standard "trend strength" read on a cumulative indicator,
analogous to the OBV-vs-its-own-EMA and Klinger constructions already
validated in this repo) as a rolling z-scored + tanh-squashed [-1,1]
sizing dial within an SMA(trend_window) uptrend gate, deadband to cut
turnover, leverage_cap for crypto -- directly targeting the persistent
near-miss pattern (Sharpe just below 1.0, every other validator already
passing) with the same continuous-sizing fix that has repeatedly rescued
similar near-misses for RMI/RMO/McGinley/Anchored Momentum/STC/Dorsey RVI
in this repo.

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


def _asi(df: pd.DataFrame) -> pd.Series:
    """Wilder Accumulative Swing Index (cumulative sum of the Swing Index)."""
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    prev_close = close.shift(1)
    prev_open = open_.shift(1)

    r = pd.concat(
        [
            (high - close).abs(),
            (low - close).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    r = r.replace(0.0, np.nan)

    si = 50.0 * (
        (close - prev_close)
        + 0.5 * (prev_close - prev_open)
        + 0.25 * (close - open_)
    ) / r
    si = si.fillna(0.0)
    asi = si.cumsum()
    return asi


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
    asi_ema_span: int = 20,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    ASI minus its own EMA(asi_ema_span) is rolling z-scored over
    `zscore_window` bars and tanh-squashed to [-1,+1] before use as a
    sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    asi = _asi(df)
    asi_ema = asi.ewm(span=asi_ema_span, adjust=False).mean()
    diff = asi - asi_ema

    roll_mean = diff.rolling(zscore_window).mean()
    roll_std = diff.rolling(zscore_window).std()
    zscore = (diff - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    asi_ema_span: int = 20,
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
        asi_ema_span=asi_ema_span,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

"""Strategy: SMA(trend_window) directional gate with continuous BRAR
(AR/BR sentiment ratio) sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
BRAR is a pair of Chinese-market sentiment indicators (per
https://www.futuhk.com/en/support/topic1_166 and
https://www.mexc.com/support/articles/how-to-use-the-brar-indicator-in-trading,
both visited this iteration via browser_exec):

    AR = SUM(High-Open, N) / SUM(Open-Low, N) * 100      (popularity index,
         open-price-centric: how much of the day's range was above vs
         below the open)
    BR = SUM(max(0, High-PrevClose), N) / SUM(max(0, PrevClose-Low), N) * 100
         (willingness index, close-to-close-centric: strong-day gains vs
         weak-day losses relative to yesterday's close)

Both center around 100 (balanced sentiment), N=26 conventionally. Source's
own stated combined rule: "when BR is lower than AR, buy the dip" (relative
BR<AR sentiment divergence signals accumulation opportunity within an
uptrend), "when AR and BR drop sharply near a peak, take profit". First
BRAR strategy in this repo -- no prior AR/BR entries found in a Stage-1
keyword search of strategies_index.jsonl.

This iteration reframes the AR-BR spread as a CONTINUOUS SIZING dial
(rolling z-score normalized + tanh-squashed to [-1,1]) rather than a
threshold trigger, inside an SMA(trend_window) uptrend gate with a
deadband to cut turnover, following this repo's established
continuous-sizing-dial pattern, leverage-cap-aware for crypto from the
start.

Source: https://www.futuhk.com/en/support/topic1_166 (exact AR/BR
formulas) and https://www.mexc.com/support/articles/how-to-use-the-brar-indicator-in-trading
(qualitative application/combined-signal context), both visited this
iteration via browser_exec (web_search returned only Korean-market blog
snippets without the numeric formula, so the exact-formula source was
fetched via browser_exec directly).

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


def _compute_ar_br(df: pd.DataFrame, window: int) -> tuple[pd.Series, pd.Series]:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    open_ = df["open"].astype(float) if "open" in df.columns else df["close"].shift(1).astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)

    ar_num = (high - open_).rolling(window).sum()
    ar_den = (open_ - low).rolling(window).sum().replace(0.0, np.nan)
    ar = 100.0 * ar_num / ar_den

    br_num = (high - prev_close).clip(lower=0.0).rolling(window).sum()
    br_den = (prev_close - low).clip(lower=0.0).rolling(window).sum().replace(0.0, np.nan)
    br = 100.0 * br_num / br_den

    return ar, br


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
    brar_window: int = 26,
    zscore_window: int = 60,
    base_exposure: float = 0.4,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    The AR-BR spread ("when BR is lower than AR, buy the dip") is rolling
    z-score normalized then tanh-squashed to bounded [-1,1], used as a
    sizing dial gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    ar, br = _compute_ar_br(df, brar_window)
    spread = (ar - br).fillna(0.0)
    roll_mean = spread.rolling(zscore_window, min_periods=zscore_window).mean()
    roll_std = spread.rolling(zscore_window, min_periods=zscore_window).std().replace(0.0, np.nan)
    z = ((spread - roll_mean) / roll_std).fillna(0.0)
    dial = np.tanh(z)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    brar_window: int = 26,
    zscore_window: int = 60,
    base_exposure: float = 0.4,
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
        brar_window=brar_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

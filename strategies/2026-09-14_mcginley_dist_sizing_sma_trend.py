"""Strategy: SMA(trend_window) directional gate with continuous McGinley
Dynamic distance sizing overlay + deadband, leverage-cap-aware for crypto
from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
McGinley Dynamic (John R. McGinley, 1990): an adaptive moving average that
speeds up in fast/volatile markets and slows in calm ones, via
    MD_i = MD_{i-1} + (Close - MD_{i-1}) / (k * N * (Close / MD_{i-1})^4)
with k=0.6 (standard constant). Formula confirmed via Google AI-overview
synthesis of Investopedia/Groww/Capital.com/Tradejini (browser_exec
fallback -- web_search's DDGS backend was not attempted for this specific
query given repeated recent failures this cron trigger; browser_exec used
directly per the documented fallback guidance).

This repo has 6+ prior McGinley Dynamic entries (2026-09-04-127 fast/slow
crossover, 2026-09-08-020 fixed-hold reversal, 2026-09-09-049 trend-gated
crossover, 2026-09-10-096 single-line slope confirmation), all binary
crossover/slope/hold-period triggers, none using MD as a continuous sizing
dial. This iteration measures the percentage distance of price from its own
McGinley Dynamic line ((close-MD)/MD), rolling z-scored and tanh-squashed to
[-1,+1], used as a sizing multiplier within an SMA(trend_window) uptrend
gate -- following this cron trigger's validated continuous-sizing-dial
pattern. First McGinley Dynamic continuous-sizing variant in this repo.

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


def _mcginley_dynamic(close: pd.Series, n: int, k: float = 0.6) -> pd.Series:
    """McGinley Dynamic adaptive moving average.

    MD_i = MD_{i-1} + (Close - MD_{i-1}) / (k * N * (Close/MD_{i-1})^4)
    Seeded with the first close value.
    """
    close_vals = close.to_numpy()
    md = np.empty_like(close_vals, dtype=float)
    md[:] = np.nan
    first_valid = 0
    md[first_valid] = close_vals[first_valid]
    for i in range(first_valid + 1, len(close_vals)):
        prev = md[i - 1]
        c = close_vals[i]
        if prev == 0 or np.isnan(prev):
            md[i] = c
            continue
        ratio = c / prev
        denom = k * n * (ratio ** 4)
        if denom == 0 or not np.isfinite(denom):
            md[i] = prev
            continue
        md[i] = prev + (c - prev) / denom
    return pd.Series(md, index=close.index)


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
    md_n: int = 14,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Distance = (close - MD) / MD, unbounded, so rolling-z-scored over
    `zscore_window` bars and tanh-squashed to [-1,+1] before use as a sizing
    dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    md = _mcginley_dynamic(close, md_n)
    distance = (close - md) / md.replace(0.0, np.nan)
    roll_mean = distance.rolling(zscore_window).mean()
    roll_std = distance.rolling(zscore_window).std()
    zscore = (distance - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    md_n: int = 14,
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
        md_n=md_n,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

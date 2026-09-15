"""Strategy: SMA(trend_window) directional gate with continuous inverse
Donchian Channel Width volatility-compression sizing overlay + deadband,
leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-15-040, this cron trigger):
Donchian Channel Width (per sdk-trading.com's formula breakdown, visited
this iteration): upper = HighestHigh(N), lower = LowestLow(N), width =
upper - lower -- the raw range spanned by the current rolling window's
price extremes. This is fundamentally different from stdev-based
volatility measures (Bollinger Band width, ATR): it records the distance
between two rolling EXTREMES rather than statistical dispersion, and can
stay wide even after recent candles have quieted down if an older extreme
is still inside the lookback window (source's own "why width can stay
wide" point).

No first-party numeric trading rule was found on the source page (it is a
descriptive/educational reference, not a strategy guide), so this
iteration's mechanical trading rule is this repo's own economic reasoning,
applying the same well-established "volatility compression -> scale
exposure up, expansion -> scale exposure down" conditioning logic already
validated for several other volatility-range indicators in this repo
(e.g. GAPO 2026-09-14-137, Choppiness variants): normalized width
(width/close, so it's comparable across price levels and instruments) is
min-max normalized over a rolling window and INVERTED (low normalized
width/compression -> high dial value -> scale exposure UP; wide
range/expansion -> scale exposure DOWN), used as a continuous sizing
multiplier inside an SMA(trend_window) uptrend gate, with a deadband to
cut turnover. First Donchian-Width-specific strategy in this repo
(distinct from existing Donchian breakout entries, which use the
channel's boundary levels as entry/exit triggers rather than its width as
a sizing signal).

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


def _donchian_norm_width(df: pd.DataFrame, donchian_window: int) -> pd.Series:
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]

    upper = high.rolling(donchian_window).max()
    lower = low.rolling(donchian_window).min()
    width = upper - lower
    norm_width = width / close.replace(0.0, np.nan)
    return norm_width


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
    donchian_window: int = 20,
    minmax_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Normalized Donchian Channel width (width/close) is min-max normalized
    over `minmax_window` into [0,1] and INVERTED (compression=1,
    expansion=0) before being centered to [-1,1] and used as a sizing
    dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    norm_width = _donchian_norm_width(df, donchian_window)

    roll_min = norm_width.rolling(minmax_window).min()
    roll_max = norm_width.rolling(minmax_window).max()
    roll_range = (roll_max - roll_min).replace(0.0, np.nan)
    scaled = ((norm_width - roll_min) / roll_range).clip(0.0, 1.0)
    # Invert: compression (low width) -> high dial; expansion -> low dial.
    dial = (1.0 - scaled.fillna(0.5)) * 2.0 - 1.0  # map [0,1] -> [-1,1]

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    donchian_window: int = 20,
    minmax_window: int = 100,
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
        donchian_window=donchian_window,
        minmax_window=minmax_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

"""Strategy: SMA(trend_window) directional gate with continuous Order Flow
Imbalance (OFI) proxy sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per https://theledgermind.com/order-flow-imbalance-indicator/ (and
https://dm13450.github.io/2022/02/02/Order-Flow-Imbalance.html for the
underlying microstructure rationale): order flow imbalance -- the net
difference between aggressive buy volume and aggressive sell volume --
tends to precede directional price movement because it reflects real-time
demand/supply pressure rather than lagging price action. This repo's
data/loaders.py only exposes daily OHLCV (no tick-level bid/ask aggressor
data), so a standard intrabar proxy is used: buy_volume = volume *
(close-low)/(high-low), sell_volume = volume * (high-close)/(high-low)
(the same range-position-of-close proxy underlying Chaikin Money Flow's
multiplier, but consumed here as a raw net-delta series rather than a
smoothed money-flow ratio). This is DISTINCT from the already-rejected
Cumulative-Delta-Divergence entry (2026-09-08-019, which used OBV as a
cumulative-delta proxy and a rare swing-pivot divergence trigger that fired
only 4 times in 8.7 years) -- here the daily OFI proxy is rolling z-scored
and used as a CONTINUOUS SIZING dial (the pattern that has rescued many
adaptive-indicator near-misses in this repo: VAMA, FRAMA, KAMA, T3, DPO)
inside an SMA(trend_window) uptrend gate + deadband, rather than a rare
discrete divergence-confirmation entry. First OFI-proxy continuous-sizing
variant in this repo.

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


def _ofi_proxy(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """Intrabar buy/sell volume-imbalance proxy (net delta per bar).

    buy_volume = volume * (close-low)/(high-low)
    sell_volume = volume * (high-close)/(high-low)
    delta = buy_volume - sell_volume, in [-volume, +volume].
    """
    rng = (high - low).replace(0.0, np.nan)
    close_loc = (close - low) / rng
    close_loc = close_loc.clip(lower=0.0, upper=1.0).fillna(0.5)
    buy_vol = volume * close_loc
    sell_vol = volume * (1.0 - close_loc)
    delta = buy_vol - sell_vol
    return delta.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ofi_smooth_window: int = 5,
    zscore_window: int = 60,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Daily OFI-proxy delta is smoothed (ofi_smooth_window), rolling z-scored
    (zscore_window) and tanh-squashed to [-1,1], then used as a sizing dial
    inside an SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]

    trend_long = close > close.rolling(trend_window).mean()

    delta = _ofi_proxy(high, low, close, volume)
    smoothed = delta.rolling(ofi_smooth_window).mean()

    roll_mean = smoothed.rolling(zscore_window).mean()
    roll_std = smoothed.rolling(zscore_window).std().replace(0.0, np.nan)
    z = (smoothed - roll_mean) / roll_std
    dial = np.tanh(z.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ofi_smooth_window: int = 5,
    zscore_window: int = 60,
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
        ofi_smooth_window=ofi_smooth_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

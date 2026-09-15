"""Strategy: SMA(trend_window) directional gate with continuous inverse
Volatility Switch [VOLSWITCH] sizing overlay + deadband, leverage-cap-aware
for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Volatility Switch (VOLSWITCH), by Ron McEwan (Stocks & Commodities Feb
2013), per LazyBear's TradingView port visited this iteration
(https://www.tradingview.com/v/50YzpVDY/): "estimates current volatility
in respect to historical data, thus indicating whether the market is
trending or in mean reversion mode. Range is normalized to 0-1... When
Volatility Switch rises above the 0.5 level, volatility in the market is
increasing, thus the price action can be expected to become choppier with
abrupt moves. When the indicator falls below the 0.5 level from recent
high readings, volatility decreases, which may be considered a sign of
trend formation." The source's own suggested rule: VOLSWITCH<0.5 favors
trend-following, VOLSWITCH>0.5 favors mean-reversion/choppy conditions.
The underlying construction (per a secondary thinkorswim reference
description, page itself 404'd this iteration): the rolling standard
deviation of the ratio of the bar-to-bar price DIFFERENCE to the
arithmetical MEAN of the current and prior price (i.e. std-dev of a
symmetric %-change-like measure), then normalized to [0,1] over a longer
lookback. First VOLSWITCH-specific strategy in this repo -- distinct from
Choppiness Index/ADX/VHF/Donchian-Width trend-strength/vol-regime gates
already tested (different std-dev-of-symmetric-return-ratio construction,
not a range-based or directional-movement-based measure).

This iteration reframes VOLSWITCH as a CONTINUOUS SIZING dial (already
naturally normalized [0,1] before inversion): INVERTED so low-VOLSWITCH
(volatility decreasing, trend forming per the source's own guidance) scales
exposure UP and high-VOLSWITCH (choppy) scales exposure DOWN, rescaled to
[-1,1], used as an exposure multiplier inside an SMA(trend_window) uptrend
gate with a deadband to cut turnover, following this repo's established
continuous-sizing-dial pattern for volatility-regime indicators (cf.
Donchian Channel Width inverse-vol sizing, 2026-09-15-040).

Source: https://www.tradingview.com/v/50YzpVDY/ (visited this iteration,
browser_exec fallback after web_search returned garbage/unrelated results
for the discovery query).

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


def _volswitch_raw(close: pd.Series, vs_period: int) -> pd.Series:
    """Rolling standard deviation of the symmetric price-change ratio
    2*(close[t]-close[t-1]) / (close[t]+close[t-1]) over `vs_period` bars.
    """
    diff = close.diff()
    mean_price = (close + close.shift(1)) / 2.0
    ratio = diff / mean_price.replace(0.0, np.nan)
    raw_vol = ratio.rolling(vs_period).std()
    return raw_vol


def _volswitch_normalized(raw_vol: pd.Series, norm_window: int) -> pd.Series:
    """Min-max normalize the raw volatility measure to [0,1] over a longer
    rolling lookback window, matching VOLSWITCH's own [0,1] convention.
    """
    roll_min = raw_vol.rolling(norm_window).min()
    roll_max = raw_vol.rolling(norm_window).max()
    roll_range = (roll_max - roll_min).replace(0.0, np.nan)
    normed = (raw_vol - roll_min) / roll_range
    return normed.clip(lower=0.0, upper=1.0)


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
    vs_period: int = 14,
    norm_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    VOLSWITCH (normalized [0,1]) is INVERTED (low VOLSWITCH = trend forming
    = high dial) and rescaled to [-1,+1] via 2*(1-x)-1 before use as a
    sizing dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    raw_vol = _volswitch_raw(close, vs_period)
    volswitch = _volswitch_normalized(raw_vol, norm_window)
    dial = (2.0 * (1.0 - volswitch.fillna(0.5))) - 1.0

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    vs_period: int = 14,
    norm_window: int = 100,
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
        vs_period=vs_period,
        norm_window=norm_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

"""Strategy: SMA(trend_window) directional gate with continuous Demand
Index (Sibbet) sizing overlay + deadband, with the leverage-cap crypto
recalibration established earlier this cron trigger applied from the
start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
James Sibbet's Demand Index (formula per
https://www.luxalgo.com/library/indicator/demand-index/, read via
browser_exec this iteration -- web_search's DuckDuckGo backend TLS-errored
on every query attempted): volume, normalized by its recent average, is
split into buying and selling pressure components scaled by the size of
a volatility-scaled move in a weighted price (H+L+2C)/4; the two pressure
components are averaged over a pressure window and their signed ratio
forms a zero-centered oscillator, explicitly designed by its source to be
read gradiently -- "cross above zero: buying pressure has overtaken
selling... Spike beyond +3: an extreme buying-pressure reading" -- i.e.
the source itself frames DI as naturally amenable to graded/continuous
interpretation, not just a binary zero-cross trigger.

This repo has 1 prior Demand Index entry (2026-09-08-012, binary zero-line
crossover ENTRY trigger, rejected). This iteration is the first to reframe
DI as a CONTINUOUS SIZING dial, reusing this cron trigger's established
pattern. Learning directly from this cron trigger's own leverage-cap
finding (2026-09-14-124/125: continuous sizing dials need a LOWER
leverage_cap on crypto than the equity default to control absolute
drawdown), this strategy is parameterized with separable
`leverage_cap`/`base_exposure` defaults intended to be swept low for
crypto from the start rather than defaulting to 1.0x and rejecting on MDD
first.

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


def _demand_index(
    df: pd.DataFrame,
    pressure_window: int = 10,
    vol_norm_window: int = 10,
    volatility_window: int = 10,
    smoothing: int = 3,
) -> pd.Series:
    """Sibbet's Demand Index, simplified per LuxAlgo's public description.

    weighted_price = (High + Low + 2*Close) / 4
    price_change = weighted_price.diff()
    vol_scaled_change = price_change / rolling_mean(TrueRange, volatility_window)
    norm_volume = Volume / rolling_mean(Volume, vol_norm_window)
    buy_pressure = norm_volume where vol_scaled_change > 0, scaled by |vol_scaled_change|
    sell_pressure = norm_volume where vol_scaled_change < 0, scaled by |vol_scaled_change|
    DI_raw = (avg(buy_pressure, pressure_window) - avg(sell_pressure, pressure_window)) /
             (avg(buy_pressure, pressure_window) + avg(sell_pressure, pressure_window))
    DI = EMA(DI_raw, smoothing) -- naturally bounded roughly [-1, 1] with
    this ratio construction (source's own +/-3 extreme levels use a
    different raw-magnitude-based construction; this repo uses the
    bounded-ratio variant for direct comparability with other sizing
    dials this cron trigger).
    """
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    weighted_price = (high + low + 2 * close) / 4.0
    price_change = weighted_price.diff()
    vol_scaled_change = price_change / true_range.rolling(volatility_window).mean().replace(0, np.nan)
    norm_volume = volume / volume.rolling(vol_norm_window).mean().replace(0, np.nan)

    magnitude = norm_volume * vol_scaled_change.abs()
    buy_pressure = magnitude.where(vol_scaled_change > 0, other=0.0)
    sell_pressure = magnitude.where(vol_scaled_change < 0, other=0.0)

    buy_avg = buy_pressure.rolling(pressure_window).mean()
    sell_avg = sell_pressure.rolling(pressure_window).mean()
    denom = (buy_avg + sell_avg).replace(0, np.nan)
    di_raw = (buy_avg - sell_avg) / denom

    di = di_raw.ewm(span=smoothing, adjust=False).mean()
    return di.clip(lower=-1.0, upper=1.0)


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
    pressure_window: int = 10,
    vol_norm_window: int = 10,
    volatility_window: int = 10,
    di_smoothing: int = 3,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    di = _demand_index(
        df,
        pressure_window=pressure_window,
        vol_norm_window=vol_norm_window,
        volatility_window=volatility_window,
        smoothing=di_smoothing,
    )

    raw_exposure = base_exposure + sensitivity * di
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    pressure_window: int = 10,
    vol_norm_window: int = 10,
    volatility_window: int = 10,
    di_smoothing: int = 3,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        pressure_window=pressure_window,
        vol_norm_window=vol_norm_window,
        volatility_window=volatility_window,
        di_smoothing=di_smoothing,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

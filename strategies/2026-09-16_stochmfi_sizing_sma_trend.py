"""Strategy: SMA(trend_window) directional gate with continuous Stochastic
MFI (Stochastic applied to the Money Flow Index) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Stochastic Money Flow Index (StochMFI), per
https://www.tradingview.com/script/DSkMPdY2-Stochastic-Money-Flow-Index/
(iambrennanwalsh, visited this iteration): "a variation of the classic
Stochastic RSI that uses the Money Flow Index (MFI) rather than the
Relative Strength Index (RSI) in its calculation. While the RSI focuses
solely on price momentum, the MFI is a volume-weighted indicator,
meaning it incorporates both price and volume data. The Stochastic MFI is
intended to provide a more precise and sensitive reading of the MFI by
measuring the level of the MFI relative to its range over a specific
period." This repo already has plain MFI entries and this cron trigger's
StochCMO/Stochastic-RVI entries applied the same "Stochastic-of-oscillator"
generalization to CMO and Dorsey's RVI respectively -- this is the
volume-weighted MFI-source variant, first StochMFI construction in this
repo, and the first of this trigger's Stochastic-of-oscillator family that
incorporates volume data (not just price).

Money Flow Index (standard): typical_price = (H+L+C)/3, raw_money_flow =
typical_price * volume, split into positive/negative flow buckets by the
sign of typical_price's day-over-day change, money_flow_ratio =
sum(positive_flow, n) / sum(negative_flow, n), MFI = 100 - 100/(1+ratio).

This iteration reframes StochMFI as a CONTINUOUS SIZING dial (already
naturally bounded [0,1], rescaled to [-1,1] via 2x-1, no z-score/tanh
needed) used as an exposure multiplier inside an SMA(trend_window) uptrend
gate with a deadband to cut turnover, following this repo's repeatedly
validated continuous-sizing-dial pattern for oscillator families.

Source: https://www.tradingview.com/script/DSkMPdY2-Stochastic-Money-Flow-Index/
(visited this iteration, browser_exec fallback after web_search returned
an empty/garbage result for the discovery query, same recurring pattern as
this trigger's prior two Stochastic-of-oscillator entries).

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


def _mfi(df: pd.DataFrame, mfi_period: int) -> pd.Series:
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    typical_price = (high + low + close) / 3.0
    raw_money_flow = typical_price * volume
    tp_diff = typical_price.diff()

    positive_flow = raw_money_flow.where(tp_diff > 0, 0.0)
    negative_flow = raw_money_flow.where(tp_diff < 0, 0.0)

    pos_sum = positive_flow.rolling(mfi_period).sum()
    neg_sum = negative_flow.rolling(mfi_period).sum().replace(0.0, np.nan)

    money_flow_ratio = pos_sum / neg_sum
    mfi = 100.0 - (100.0 / (1.0 + money_flow_ratio))
    return mfi


def _stoch_of_series(series: pd.Series, stoch_period: int) -> pd.Series:
    lo = series.rolling(stoch_period).min()
    hi = series.rolling(stoch_period).max()
    rng = (hi - lo).replace(0.0, np.nan)
    stoch = (series - lo) / rng
    return stoch.clip(lower=0.0, upper=1.0)


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
    mfi_period: int = 14,
    stoch_period: int = 14,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Stochastic MFI (already naturally bounded [0,1]) is rescaled to [-1,+1]
    via 2x-1 (no z-score/tanh needed since it's a native ratio) before use
    as a sizing dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    mfi = _mfi(df, mfi_period)
    stoch_mfi = _stoch_of_series(mfi, stoch_period)
    dial = (2.0 * stoch_mfi.fillna(0.5)) - 1.0

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    mfi_period: int = 14,
    stoch_period: int = 14,
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
        mfi_period=mfi_period,
        stoch_period=stoch_period,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

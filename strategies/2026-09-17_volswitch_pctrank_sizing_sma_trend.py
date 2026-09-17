"""Strategy: Volatility Switch (VOLSWITCH, Ron McEwan, TASC Feb 2013)
percentile-rank-of-own-volatility construction, reframed as an INVERSE
CONTINUOUS SIZING dial within an SMA(trend_window) uptrend gate,
leverage-cap-aware for crypto.

Hypothesis (this cron trigger, iteration 2):
Per TASC's own EasyLanguage Traders' Tips code (source:
https://traders.com/Documentation/FEEDbk_docs/2013/02/TradersTips.html,
read this iteration via browser_exec -- web_search's DDGS backend
intermittently errored/returned no results for several queries this
iteration; Google search fallback used for keyword discovery):

    dr = (Close - Close[1]) / ((Close + Close[1]) / 2)   # symmetric % change
    vol = StdDev(dr, Length)                             # rolling volatility
    Count = number of bars i in [0, Length-1] where vol[i] <= vol[current]
            (i.e. how many of the trailing Length volatility readings are
            at or below TODAY's volatility reading)
    VolSwitch = Count / Length                            # in [0, 1]

This is a PERCENTILE-RANK-of-current-volatility construction (today's vol
level's rank within its own trailing window), genuinely distinct from this
repo's existing VOLSWITCH entry (2026-09-16-095), which used a min-max
normalization approximation of the rolling std-dev instead (and rejected
on SPY with no rescue found). Economic rationale is identical to the
original (McEwan's own stated interpretation, VolSwitch<0.5 = decreasing/
low-relative volatility, historically associated with trend formation;
VolSwitch>0.5 = increasing/high-relative volatility, choppier/more
mean-reverting), so this sub-iteration retains this repo's established
inverse-volatility-conditioning sizing pattern (low VolSwitch -> higher
exposure) but swaps in the TASC-exact percentile-rank construction to see
if it fixes the prior SPY rejection.

Source: https://traders.com/Documentation/FEEDbk_docs/2013/02/TradersTips.html
(TASC's own EasyLanguage code disclosure, read via browser_exec this
iteration since this backend's web_extract cannot fetch page content,
search-only).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns).
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


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def _vol_switch(close: pd.Series, length: int) -> pd.Series:
    """TASC's exact percentile-rank-of-own-volatility construction."""
    dr = (close - close.shift(1)) / ((close + close.shift(1)) / 2.0)
    vol = dr.rolling(length).std(ddof=0)

    def _pct_rank(window: np.ndarray) -> float:
        current = window[-1]
        if np.isnan(current):
            return np.nan
        return float(np.sum(window <= current)) / len(window)

    vol_switch = vol.rolling(length).apply(_pct_rank, raw=True)
    return vol_switch


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    vol_length: int = 21,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    dial = 2*(0.5 - vol_switch), naturally bounded [-1,1] -- LOW VolSwitch
    (current volatility ranks low relative to its own recent history,
    associated with trend formation per McEwan's own interpretation)
    pushes exposure UP; HIGH VolSwitch (choppier/mean-reverting regime)
    pushes exposure DOWN, gated to 0 whenever close is below its
    SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    vol_switch = _vol_switch(close, vol_length)
    dial = 2.0 * (0.5 - vol_switch)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    vol_length: int = 21,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        vol_length=vol_length,
        sensitivity=sensitivity,
        base_exposure=base_exposure,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

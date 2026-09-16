"""Strategy: Linear-Weighted Moving Average (LWMA) distance as a CONTINUOUS
SIZING dial within an SMA(trend_window) uptrend gate, leverage-cap-aware for
crypto.

Hypothesis (this cron trigger, iteration 5):
First Linear-Weighted Moving Average strategy in this repo. Per
https://www.quantifiedstrategies.com/linear-weighted-moving-average/ (read
this iteration): LWMA puts linearly increasing weight on more recent prices
(most recent bar gets the highest weight, weight decays linearly for older
bars) so it reacts faster to price changes than a plain SMA/EMA. The
source's own SPY backtest shows a clean regime split by LWMA window length:
SHORT windows (5-25 days) favor MEAN-REVERSION (best CAGR when buying on a
close crossing BELOW the average and selling on a cross back ABOVE -- e.g.
Strategy-1's 5-day-LWMA CAGR 8.53% vs Strategy-2's 5-day-LWMA CAGR only
1.09%), while LONG windows (100-200 days) favor TREND-FOLLOWING (buy above,
sell below -- Strategy-2's 200-day CAGR 6.21% clearly beats Strategy-1's
200-day CAGR 3.28%).

This iteration reframes that binary regime split as a single CONTINUOUS
sizing dial rather than two separate strategies, following this repo's
established binary-threshold-to-continuous-sizing-dial rescue pattern (DPO,
Hurst, VHF, TII, RVI, MAMA-FAMA spread, Kalman slope, CBOE SKEW, Ichimoku
Kumo-distance, VPT-ROC, etc.): compute a SHORT LWMA (fast, mean-reversion
window) and a LONG LWMA (slow, trend window). The dial is the rolling
z-scored, tanh-squashed distance between price and the SHORT LWMA, but its
SIGN is inverted (mean-reversion: price far below short LWMA => increase
exposure, betting on reversion) -- but this only applies within an uptrend
gate defined by the LONG LWMA (close > long LWMA), operationalizing the
source's implicit combined regime: only mean-revert on short-term dips
while the longer-term trend (long LWMA) remains up. This is a genuinely
distinct construction from every prior "distance from MA" continuous dial
in this repo (which have all used SMA/EMA, never a linearly-weighted MA).

Source: https://www.quantifiedstrategies.com/linear-weighted-moving-average/
(read via browser_exec this iteration).

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


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def _lwma(close: pd.Series, window: int) -> pd.Series:
    """Linear-weighted moving average: weights increase linearly 1..window,
    most recent bar gets the highest weight."""
    weights = np.arange(1, window + 1, dtype=float)
    return close.rolling(window).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def generate_signals(
    price_df: pd.DataFrame,
    short_lwma_window: int = 10,
    long_lwma_window: int = 100,
    zscore_window: int = 126,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    dial = -tanh(zscore((close - short_LWMA)/short_LWMA, zscore_window)) --
    price further BELOW the short LWMA (a dip) pushes the dial positive
    (increase exposure, mean-reversion bet); price further ABOVE pushes it
    negative (reduce exposure), gated to 0 whenever close is below the LONG
    LWMA (long-term trend filter).
    """
    df = _prep(price_df)
    close = df["close"]

    short_lwma = _lwma(close, short_lwma_window)
    long_lwma = _lwma(close, long_lwma_window)

    trend_long = close > long_lwma

    rel_dist = (close - short_lwma) / short_lwma
    roll_mean = rel_dist.rolling(zscore_window).mean()
    roll_std = rel_dist.rolling(zscore_window).std(ddof=0)
    z = (rel_dist - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = -np.tanh(z.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    short_lwma_window: int = 10,
    long_lwma_window: int = 100,
    zscore_window: int = 126,
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
        short_lwma_window=short_lwma_window,
        long_lwma_window=long_lwma_window,
        zscore_window=zscore_window,
        sensitivity=sensitivity,
        base_exposure=base_exposure,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

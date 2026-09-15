"""Strategy: SMA(trend_window) directional gate with continuous
Corwin-Schultz bid-ask spread-estimator sizing overlay (inverse
relationship: exposure shrinks as the estimated spread/liquidity-stress
z-score rises) + deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Corwin & Schultz (2012, Journal of Finance) two-bar high-low bid-ask
spread estimator, already confirmed and implemented in this repo (see
strategies/2026-09-11_corwin_schultz_spread_regime.py, id 2026-09-11-002):
daily high/low ranges widen mechanically both from volatility AND from the
bid-ask bounce; the CS estimator statistically separates the two,
producing a rolling estimate of the effective bid-ask spread from OHLC
data alone. Source: https://www.tradingview.com/script/ji4eKKuZ-Corwin-Schultz-Spread-Bands/
(already visited/logged in this repo's ledger; formula re-used unchanged,
no new fetch this iteration).

This repo has 3 prior Corwin-Schultz entries, ALL using the spread as a
binary STRESS-EXIT EVENT trigger (enter when the smoothed spread crosses
back below a rolling stress threshold): 2026-09-11-002 (plain version,
QQQ near-miss Sharpe 0.778), 2026-09-11-003 (added vol-regime AND-gate,
made QQQ worse), 2026-09-11-005 (per-symbol parameter retune, accepted QQQ
only at Sharpe 1.093, SPY near-miss). None used the spread as a
CONTINUOUS SIZING dial. This iteration reframes the identical formula
that way: exposure inversely scales with the rolling spread's own z-score
(tanh-squashed, no hard event/threshold), inside an SMA(trend_window)
uptrend gate -- the same continuous-sizing-dial construction pattern that
has rescued/broadened numerous other binary-trigger indicator families in
this repo (Vortex, TSI, RMI, Amihud ILLIQ this same cron trigger, etc.),
applied here for the first time to the Corwin-Schultz liquidity/
microstructure-proxy family specifically.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_K = 3 - 2 * np.sqrt(2)


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _corwin_schultz_spread(high: pd.Series, low: pd.Series, smooth: int) -> pd.Series:
    log_hl = np.log(high / low)
    beta = log_hl ** 2 + log_hl.shift(1) ** 2

    hh = pd.concat([high, high.shift(1)], axis=1).max(axis=1)
    ll = pd.concat([low, low.shift(1)], axis=1).min(axis=1)
    gamma = (np.log(hh / ll)) ** 2

    with np.errstate(invalid="ignore"):
        alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / _K - np.sqrt(gamma / _K)

    raw_spread = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
    raw_spread = raw_spread.clip(lower=0.0, upper=1.0)
    smoothed = raw_spread.ewm(span=smooth, adjust=False, min_periods=smooth).mean()
    return smoothed


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
    spread_smooth: int = 5,
    zscore_window: int = 252,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    exposure = clip(base_exposure - sensitivity * tanh(spread_zscore), 0, cap)
    gated to 0 whenever close is below its SMA(trend_window) (uptrend gate).
    Elevated estimated spread (positive z, liquidity stress) shrinks
    exposure; unusually tight/liquid conditions (negative z) expand it
    toward leverage_cap.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    trend_long = close > close.rolling(trend_window).mean()
    spread = _corwin_schultz_spread(high, low, spread_smooth)

    roll_mean = spread.rolling(zscore_window, min_periods=spread_smooth).mean()
    roll_std = spread.rolling(zscore_window, min_periods=spread_smooth).std()
    zscore = (spread - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure - sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)
    raw_exposure = raw_exposure.where(~zscore.isna(), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    spread_smooth: int = 5,
    zscore_window: int = 252,
    base_exposure: float = 0.5,
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
        spread_smooth=spread_smooth,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

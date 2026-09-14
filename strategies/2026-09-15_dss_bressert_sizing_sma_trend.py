"""Strategy: SMA(trend_window) directional gate with continuous DSS Bressert
(Double Smoothed Stochastic, Walter Bressert + William Blau) sizing overlay
+ deadband, leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-15-033, this cron trigger):
DSS Bressert, per https://www.prorealcode.com/prorealtime-indicators/dss-bressert-double-smoothed-stochastic/
and Google's AI-overview summary (visited this iteration):
  sto1     = %K stochastic of close over PDS bars = 100 * (close - LL(PDS)) / (HH(PDS) - LL(PDS))
  xPreCalc = EMA(sto1, EMAlen)
  sto2     = 100 * (xPreCalc - rolling_min(xPreCalc, PDS)) / (rolling_max(xPreCalc, PDS) - rolling_min(xPreCalc, PDS))
  xDSS     = EMA(sto2, EMAlen)
  xTrigger = EMA(xDSS, TriggerLen)

This is a genuinely new indicator family for this repo (0 prior
strategies/log entries reference "Bressert" or "DSS"). The indicator's own
interpretation (per its creators and every source consulted) is a 0-100
bounded oscillator read the same way as a standard stochastic:
overbought>80, oversold<20, with the double-EMA smoothing specifically
intended to cut choppy noise vs a single-smoothed stochastic. Rather than a
discrete overbought/oversold threshold-cross rule (the repo's log shows
this family of rule consistently underperforms bare z-score/tanh continuous
dials for oscillator-type indicators -- see the McGinley Dynamic, WaveTrend
CI, and Gann HiLo continuous-sizing entries this same cron trigger), this
implementation reuses the established continuous-sizing-dial pattern: xDSS
is centered on its 50 midpoint, rolling z-scored over `zscore_window`, and
tanh-squashed into [-1,+1] as an exposure multiplier inside an
SMA(trend_window) uptrend gate, with a deadband to cut turnover. This turns
the already-bounded [0,100] oscillator into a smoothly graded, always-
available sizing input rather than a sparse discrete zone-crossing event.

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


def _dss_bressert(close: pd.Series, pds: int, ema_len: int, trigger_len: int):
    ll = close.rolling(pds).min()
    hh = close.rolling(pds).max()
    sto1 = 100.0 * (close - ll) / (hh - ll).replace(0.0, np.nan)

    x_precalc = sto1.ewm(span=ema_len, adjust=False).mean()

    pc_min = x_precalc.rolling(pds).min()
    pc_max = x_precalc.rolling(pds).max()
    sto2 = 100.0 * (x_precalc - pc_min) / (pc_max - pc_min).replace(0.0, np.nan)

    x_dss = sto2.ewm(span=ema_len, adjust=False).mean()
    x_trigger = x_dss.ewm(span=trigger_len, adjust=False).mean()
    return x_dss, x_trigger


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
    pds: int = 10,
    ema_len: int = 9,
    trigger_len: int = 5,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    xDSS (the double-smoothed stochastic, 0-100 scale) is centered on 50,
    rolling z-scored over `zscore_window` bars, and tanh-squashed to
    [-1,+1] before use as a sizing dial, gated by an SMA(trend_window)
    uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    x_dss, _x_trigger = _dss_bressert(close, pds, ema_len, trigger_len)

    centered = x_dss - 50.0
    roll_mean = centered.rolling(zscore_window).mean()
    roll_std = centered.rolling(zscore_window).std()
    zscore = (centered - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    pds: int = 10,
    ema_len: int = 9,
    trigger_len: int = 5,
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
        pds=pds,
        ema_len=ema_len,
        trigger_len=trigger_len,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

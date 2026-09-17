"""Strategy: SMA(trend_window) directional gate with continuous Exponential
Standard Deviation (ESD) Bands %B sizing overlay + deadband, leverage-cap
aware for crypto from the start.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-140):
Vitali Apirine's Exponential Standard Deviation (ESD) Bands (TASC Feb 2017;
TradeStation code disclosed at
https://traders.com/Documentation/FEEDbk_docs/2017/02/TradersTips.html):
MidLine = EMA(close, length); ExpSDev = the EMA-weighted standard deviation
of close around that EMA (source's own ExpStdDev function: mean-squared
deviation from the EMA midline, computed the same recursive way as Bollinger
Bands but with an exponential-average basis instead of simple). UpperBand /
LowerBand = MidLine +/- NumDevs * ExpSDev. The source article presents ESD
Bands purely as a volatility/trend-visualization indicator ("suggests it can
be used as a confirming indication along with other indicators such as the
ADX") with NO disclosed mechanical trading rule -- this iteration follows
this cron trigger's own validated pattern (already rescued Kirshenbaum,
STARC, Keltner, Bollinger, Acceleration Bands, Elder AutoEnvelope, Standard
Error Bands from discrete-trigger rejections in this repo): reframe the band
as a Bollinger-%B-style CONTINUOUS SIZING dial,
    esd_pctb = (close - lower) / (upper - lower)
naturally centered ~0.5, rescaled to a zero-centered dial via
(pctb - 0.5) * 2, clipped to [-1, 1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate with a deadband to cut turnover. First ESD
Bands strategy in this repo -- distinct from Bollinger Bands (SMA + raw
stddev) and Kirshenbaum Bands (EMA + linear-regression stderr) since ESD
uses an EMA-weighted (not simple/regression-residual) standard deviation
computed around an EMA centerline.

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


def _exp_std_dev(close: pd.Series, length: int) -> pd.Series:
    """EMA-weighted standard deviation of close around its own EMA.

    Mirrors the source's ExpStdDev function: for each bar, take the
    trailing `length` closes, compute their mean-squared deviation from the
    CURRENT EMA value (not each historical EMA value -- source uses
    XAverage(Price,Length) as a single reference per window), sqrt it.
    """
    ema = close.ewm(span=length, adjust=False, min_periods=length).mean()

    def _win_std(vals: np.ndarray, ema_ref: float) -> float:
        sq = (vals - ema_ref) ** 2
        return float(np.sqrt(sq.sum() / len(vals)))

    result = pd.Series(np.nan, index=close.index)
    close_vals = close.to_numpy()
    ema_vals = ema.to_numpy()
    n = len(close)
    for i in range(length - 1, n):
        window = close_vals[i - length + 1 : i + 1]
        result.iloc[i] = _win_std(window, ema_vals[i])
    return result


def _esd_pctb(df: pd.DataFrame, length: int, num_devs: float) -> pd.Series:
    close = df["close"]
    midline = close.ewm(span=length, adjust=False, min_periods=length).mean()
    esd = _exp_std_dev(close, length)
    upper = midline + num_devs * esd
    lower = midline - num_devs * esd
    band_width = (upper - lower).replace(0.0, np.nan)
    pctb = (close - lower) / band_width
    return pctb


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
    esd_length: int = 20,
    esd_num_devs: float = 2.0,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pctb = _esd_pctb(df, esd_length, esd_num_devs)
    pctb_centered = ((pctb - 0.5) * 2.0).clip(-1.0, 1.0)

    raw_exposure = base_exposure + sensitivity * pctb_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    esd_length: int = 20,
    esd_num_devs: float = 2.0,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        esd_length=esd_length,
        esd_num_devs=esd_num_devs,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strategy_ret

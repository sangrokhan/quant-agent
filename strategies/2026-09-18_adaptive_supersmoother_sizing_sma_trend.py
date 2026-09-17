"""Strategy: SMA(trend_window) directional gate with continuous Ehlers
Adaptive SuperSmoother deviation sizing overlay + deadband, leverage-cap-aware
for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
John F. Ehlers' "Adaptive SuperSmoother" (TASC September 2026 article, code
per https://traders.com/Documentation/FEEDbk_docs/2026/09/TradersTips.html
TradeStation EasyLanguage block, re-confirmed this iteration): a fixed-period
2-pole SuperSmoother low-pass filter (SS) has its own 1-bar rate-of-change
(ROC1 = SS - SS[1]) RMS-normalized over an 81-bar window (ROCRMS), clipped
to [0,2], and the resulting adaptive period Period = Period0*(1-0.5*ROC)^2
(floored at 2) drives a second SuperSmoother pass (AdaptiveSS) that runs
faster in trending/volatile regimes and slower in quiet/choppy ones.

Repo already tested this construction TWICE as a BINARY crossover trigger
(fixed-period SuperSmoother vs adaptive-period SuperSmoother crossing):
  - 2026-09-12-146: plain crossover, rejected (near-miss on Sharpe/MDD).
  - 2026-09-17-060: crossover + realized-vol regime gate (fix attempt for
    the MDD near-miss) -- MDD fixed but now Sharpe fails on both QQQ/SPY.
Diagnosis, consistent with this repo's recurring pattern for every other
binary-crossover oscillator (Klinger, ZLEMA, Hurst, FRAMA, CKSP, etc.): a
hard binary crossover discards the CONTINUOUS information in exactly how
far price has diverged from the adaptive filter and how much the filter's
own responsiveness (ROC-derived adaptive period) has shifted. This
iteration reframes it as a CONTINUOUS SIZING dial instead: the normalized
distance (close - AdaptiveSS) / AdaptiveSS, rolling z-scored and
tanh-squashed to [-1, 1], used as an exposure dial inside an SMA(trend_window)
uptrend gate with deadband -- the repo's standard rescue pattern for
binary-crossover near-misses in this exact family. First Adaptive
SuperSmoother continuous-sizing variant in this repo (0 prior sizing-dial
attempts for this specific indicator).

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


def _supersmoother(price: pd.Series, period: float) -> np.ndarray:
    """2-pole Ehlers SuperSmoother with a FIXED period (scalar)."""
    n = len(price)
    p = price.to_numpy(dtype=float)
    out = np.zeros(n)
    period = max(float(period), 2.0)
    a0 = np.exp(-1.414 * np.pi / period)
    c1 = 2 * a0 * np.cos(1.414 * np.pi / period)
    c2 = a0 * a0
    coef1 = (1 - c1 + c2) / 2.0
    for i in range(n):
        if i < 2:
            out[i] = p[i]
        else:
            out[i] = coef1 * (p[i] + p[i - 1]) + c1 * out[i - 1] - c2 * out[i - 2]
    return out


def _rms(x: np.ndarray, length: int) -> np.ndarray:
    n = len(x)
    out = np.full(n, np.nan)
    sq = x * x
    for i in range(length - 1, n):
        out[i] = np.sqrt(np.mean(sq[i - length + 1 : i + 1]))
    return out


def _adaptive_supersmoother(price: pd.Series, period0: int, rms_length: int = 81) -> np.ndarray:
    """Ehlers Adaptive SuperSmoother per TASC Sept 2026 EasyLanguage:
    SS = SuperSmoother(Close, Period0)
    ROC1 = SS - SS[1]; ROCRMS = RMS(ROC1, rms_length)
    ROC = clip(|ROC1/ROCRMS|, 0, 2)
    Period = Period0*(1-0.5*ROC)^2, floored at 2
    AdaptiveSS = SuperSmoother(Close, Period) -- computed bar-by-bar with the
    per-bar-varying period (recursive 2-pole filter, coefficients recomputed
    each bar from that bar's adaptive Period).
    """
    n = len(price)
    p = price.to_numpy(dtype=float)
    ss = _supersmoother(price, period0)
    roc1 = np.diff(ss, prepend=ss[0])
    rocrms = _rms(roc1, rms_length)
    with np.errstate(invalid="ignore", divide="ignore"):
        roc = np.abs(roc1 / rocrms)
    roc = np.nan_to_num(roc, nan=0.0)
    roc = np.clip(roc, 0.0, 2.0)
    period = period0 * (1 - 0.5 * roc) ** 2
    period = np.clip(period, 2.0, None)

    out = np.zeros(n)
    for i in range(n):
        if i < 2:
            out[i] = p[i]
            continue
        per = period[i]
        a0 = np.exp(-1.414 * np.pi / per)
        c1 = 2 * a0 * np.cos(1.414 * np.pi / per)
        c2 = a0 * a0
        coef1 = (1 - c1 + c2) / 2.0
        out[i] = coef1 * (p[i] + p[i - 1]) + c1 * out[i - 1] - c2 * out[i - 2]
    return out


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
    period0: int = 20,
    zscore_window: int = 60,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.30,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    dial = tanh(sensitivity * zscore((close - AdaptiveSS) / AdaptiveSS)),
    exposure = clip(0.5 + 0.5*dial, 0, cap), gated to 0 whenever close is
    below its SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    adaptive_ss = pd.Series(_adaptive_supersmoother(close, period0), index=close.index)
    dist = (close - adaptive_ss) / adaptive_ss.replace(0.0, np.nan)

    roll_mean = dist.rolling(zscore_window).mean()
    roll_std = dist.rolling(zscore_window).std(ddof=0)
    zscore = (dist - roll_mean) / roll_std.replace(0.0, np.nan)
    zscore = zscore.fillna(0.0)

    dial = np.tanh(sensitivity * zscore)
    raw_exposure = 0.5 + 0.5 * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=1.0) * leverage_cap
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    period0: int = 20,
    zscore_window: int = 60,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.30,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        period0=period0,
        zscore_window=zscore_window,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

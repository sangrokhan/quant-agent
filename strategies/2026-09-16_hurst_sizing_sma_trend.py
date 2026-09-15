"""Strategy: SMA(trend_window) directional gate with continuous Hurst
exponent (R/S analysis) sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Direct fix attempt for prior ids 2026-09-04-155/156 and 2026-09-12-136
(rolling Hurst exponent via R/S analysis used as a BINARY trending-regime
gate on an EMA crossover, or as one leg of a 3-filter ADX+ATRpct+Hurst
regime switch -- all rejected: 2026-09-04-155 QQQ/SPY full-sample miss,
crypto decisive fail; 2026-09-04-156 inverse mean-reversion pairing, same
weak result; 2026-09-12-136 joint filter also rejected). Diagnosis
(consistent with this repo's recurring pattern for every other
oscillator/regime indicator): a hard binary threshold on H (e.g. H>0.55)
produces abrupt regime flips and whipsaw-prone flat/full-position jumps,
discarding the CONTINUOUS information in exactly how persistent or
anti-persistent the market currently is. This sub-iteration reuses this
repo's existing simplified R/S Hurst estimator (identical methodology,
unchanged from strategies/2026-09-04_hurst_regime_ema_crossover.py: split
each rolling window into sub-periods at several lengths, R/S statistic per
sub-period, H = slope of log(R/S) vs log(length) via least-squares) but
reframes H as a CONTINUOUS SIZING dial: (H-0.5)*2 rescaled to roughly
[-1,1] (H is theoretically bounded [0,1]), used directly as a sizing signal
inside an SMA(trend_window) uptrend gate with deadband -- so exposure scales
smoothly with how strongly the market is currently trending/persistent,
rather than the strategy just going all-in/all-out at a single H threshold.
Source: FractalCycles Hurst exponent guide (same source as 2026-09-04-155,
already in this repo's ledger; formula independently re-confirmed via
https://stratcraft.ai/indicators/hurst/ this iteration: "H = log(R/S) /
log(n)... Values above 0.5 suggest persistence or trending behavior").
First Hurst-exponent-as-continuous-sizing-dial strategy in this repo.

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


def _rs_stat(series: np.ndarray) -> float:
    """Classic Rescaled Range (R/S) statistic for one sub-series."""
    n = len(series)
    if n < 2:
        return np.nan
    mean = series.mean()
    deviations = series - mean
    cumulative = np.cumsum(deviations)
    r = cumulative.max() - cumulative.min()
    s = series.std(ddof=0)
    if s == 0 or np.isnan(s):
        return np.nan
    return r / s


def _hurst_exponent(window_returns: np.ndarray, sub_lengths) -> float:
    """Estimate H via simplified R/S analysis: slope of log(R/S) vs
    log(sub-period length), averaging R/S across all non-overlapping
    sub-periods of each candidate length. Unchanged from
    strategies/2026-09-04_hurst_regime_ema_crossover.py.
    """
    n = len(window_returns)
    log_lengths = []
    log_rs = []
    for length in sub_lengths:
        if length >= n or length < 8:
            continue
        n_chunks = n // length
        if n_chunks < 1:
            continue
        rs_values = []
        for i in range(n_chunks):
            chunk = window_returns[i * length : (i + 1) * length]
            rs = _rs_stat(chunk)
            if not np.isnan(rs) and rs > 0:
                rs_values.append(rs)
        if rs_values:
            log_lengths.append(np.log(length))
            log_rs.append(np.log(np.mean(rs_values)))
    if len(log_lengths) < 2:
        return np.nan
    slope, _ = np.polyfit(log_lengths, log_rs, 1)
    return float(slope)


def _rolling_hurst(close: pd.Series, hurst_window: int, n_subseries: int = 4, step: int = 5) -> pd.Series:
    """Rolling Hurst exponent, computed every `step` bars for speed and
    forward-filled in between (unchanged methodology/perf-optimization
    from strategies/2026-09-04_hurst_regime_ema_crossover.py).
    """
    log_ret = np.log(close / close.shift(1))
    sub_lengths = sorted({max(8, hurst_window // k) for k in range(1, n_subseries + 1)})

    values = [np.nan] * len(close)
    ret_arr = log_ret.values
    for i in range(hurst_window, len(close), step):
        window = ret_arr[i - hurst_window : i]
        window = window[~np.isnan(window)]
        if len(window) < hurst_window // 2:
            continue
        values[i] = _hurst_exponent(window, sub_lengths)
    result = pd.Series(values, index=close.index)
    return result.ffill()


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
    hurst_window: int = 100,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    H is theoretically bounded roughly [0,1] -- rescaled to [-1,1] via
    (H-0.5)*2, used directly (no z-score/tanh needed) as a sizing dial:
    exposure = clip(base_exposure + sensitivity*dial, 0, cap), gated to 0
    whenever close is below its SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    hurst = _rolling_hurst(close, hurst_window)
    dial = (hurst - 0.5) * 2.0
    dial = dial.clip(lower=-1.0, upper=1.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    hurst_window: int = 100,
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
        hurst_window=hurst_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

"""Strategy: Kase Peak Oscillator (Cynthia Kase) contrarian reversal -- long only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-010):
Per the exact PRT/MT4-derived formula at
https://www.prorealcode.com/prorealtime-indicators/kase-peak-oscillator-v2/,
Cynthia Kase's Peak Oscillator (KPO) normalizes a dual max-over-lookback-range
statistic (log(High/Low)/sqrt(k), scanned over k = short_cycle..long_cycle-1
bars both forward- and backward-looking from the current bar) by the recent
log-return volatility, then scales the smoothed difference by a sensitivity
factor. A "peak-out" event -- a local extreme of the oscillator that exceeds
an adaptive, volatility-scaled deviation band -- signals momentum has become
statistically extreme (Kase's own use case: "identify potential ... strategy
decisions" at momentum extremes / cite ATAS-style trading-rules writeups
describing peak-outs as reversal markers). This strategy tests the
contrarian reading required for a long-only implementation under SAFETY.md:
a NEGATIVE peak-out (bearish momentum statistically exhausted) marks a
tradeable bottom -> buy; a POSITIVE peak-out (bullish momentum statistically
exhausted) marks a tradeable top -> exit. First Kase Peak Oscillator
strategy in this repo -- distinct from all prior oscillator-threshold /
z-score / Bollinger-band mean-reversion strategies since KPO's normalization
is a volatility-scaled *dual-direction max-over-lookback-range* statistic,
not a moving-average distance or a fixed-window rolling z-score.

Signal logic
------------
- cc_log = log(close / close.shift(1)); cc_dev = rolling std(cc_log, 9);
  avg = rolling mean(cc_dev, 30) (volatility normalizer).
- For each bar i (once avg[i] > 0), scan k = short_cycle..long_cycle-1:
    x1[i] = max_k( log(High[i] / Low[i-k]) / sqrt(k) ) / avg[i]   (forward max)
    xs[i] = max_k( log(High[i-k] / Low[i]) / sqrt(k) ) / avg[i]   (backward max)
- xp = sensitivity * (SMA3(x1) - SMA3(xs))  -- the KPO line ("kpoBuffer").
- Adaptive band: tmp = rolling_mean(|xp|, 50) + deviations * rolling_std(|xp|, 50);
  max_val = max(90, tmp); min_val = min(90, tmp).
- Peak-out (one-bar-lagged, non-repainting, matches source's non-allPeaksMode):
  a bar i-1 is a NEGATIVE peak-out if kpo[i-1] < 0, kpo[i-1] < kpo[i]
  (turning back up), kpo[i-1] <= kpo[i-2], and kpo[i-1] <= -max_val[i-1].
  Mirror condition (all signs flipped, kpo[i-1] >= max_val[i-1]) for a
  POSITIVE peak-out.
- Entry (long): a negative peak-out fires at bar i (using only data through
  bar i, since it references i-1/i-2 which are already known).
- Exit: a positive peak-out fires, OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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


def _compute_kpo(
    df: pd.DataFrame,
    short_cycle: int,
    long_cycle: int,
    sensitivity: float,
) -> pd.Series:
    close = df["close"]
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    n = len(df)

    cc_log = np.log(close / close.shift(1))
    cc_dev = cc_log.rolling(9, min_periods=9).std()
    avg = cc_dev.rolling(30, min_periods=30).mean().to_numpy(dtype=float)

    log_high = np.log(high)
    log_low = np.log(low)

    max1 = np.zeros(n)
    maxs = np.zeros(n)
    ks = np.arange(short_cycle, long_cycle)
    for k in ks:
        sqrt_k = np.sqrt(k)
        # v1[i] = log(high[i] / low[i-k]) / sqrt(k), valid for i >= k
        v1 = np.full(n, -np.inf)
        v1[k:] = (log_high[k:] - log_low[: n - k]) / sqrt_k
        np.maximum(max1, v1, out=max1)
        # v2[i] = log(high[i-k] / low[i]) / sqrt(k), valid for i >= k
        v2 = np.full(n, -np.inf)
        v2[k:] = (log_high[: n - k] - log_low[k:]) / sqrt_k
        np.maximum(maxs, v2, out=maxs)

    max1 = np.clip(max1, 0.0, None)
    maxs = np.clip(maxs, 0.0, None)

    warmup = long_cycle * 2
    x1 = np.full(n, np.nan)
    xs = np.full(n, np.nan)
    valid = ~np.isnan(avg) & (avg > 0)
    valid[:warmup] = False
    x1[valid] = max1[valid] / avg[valid]
    xs[valid] = maxs[valid] / avg[valid]

    x1s = pd.Series(x1, index=df.index).rolling(3, min_periods=3).mean()
    xss = pd.Series(xs, index=df.index).rolling(3, min_periods=3).mean()
    kpo = sensitivity * (x1s - xss)
    return kpo


def _compute_peaks(kpo: pd.Series, deviations: float):
    xp_abs = kpo.abs()
    tmp_val = xp_abs.rolling(50, min_periods=50).mean() + deviations * xp_abs.rolling(
        50, min_periods=50
    ).std()
    max_val = tmp_val.clip(lower=90.0)

    kpo_arr = kpo.to_numpy(dtype=float)
    max_val_arr = max_val.to_numpy(dtype=float)
    n = len(kpo)
    neg_peak = np.zeros(n, dtype=bool)
    pos_peak = np.zeros(n, dtype=bool)

    for i in range(2, n):
        k1, k2, k3 = kpo_arr[i - 1], kpo_arr[i], kpo_arr[i - 2]
        mv1 = max_val_arr[i - 1]
        if np.isnan(k1) or np.isnan(k2) or np.isnan(k3) or np.isnan(mv1):
            continue
        if k1 > 0 and k1 > k2 and k1 >= k3 and k1 >= mv1:
            pos_peak[i] = True
        if k1 < 0 and k1 < k2 and k1 <= k3 and k1 <= -mv1:
            neg_peak[i] = True

    return (
        pd.Series(neg_peak, index=kpo.index),
        pd.Series(pos_peak, index=kpo.index),
    )


def generate_signals(
    price_df: pd.DataFrame,
    short_cycle: int = 8,
    long_cycle: int = 65,
    sensitivity: float = 40.0,
    deviations: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    kpo = _compute_kpo(df, short_cycle, long_cycle, sensitivity)
    neg_peak, pos_peak = _compute_peaks(kpo, deviations)

    n = len(df)
    neg_arr = neg_peak.to_numpy()
    pos_arr = pos_peak.to_numpy()
    pos_series = [0] * n

    in_pos = False
    hold_counter = 0
    for i in range(n):
        if in_pos:
            hold_counter += 1
            exit_now = bool(pos_arr[i]) or hold_counter >= max_hold_days
            if exit_now:
                in_pos = False
                hold_counter = 0
                pos_series[i] = 0
            else:
                pos_series[i] = 1
        else:
            if bool(neg_arr[i]):
                in_pos = True
                hold_counter = 0
                pos_series[i] = 1
            else:
                pos_series[i] = 0

    return pd.Series(pos_series, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    short_cycle: int = 8,
    long_cycle: int = 65,
    sensitivity: float = 40.0,
    deviations: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        short_cycle=short_cycle,
        long_cycle=long_cycle,
        sensitivity=sensitivity,
        deviations=deviations,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

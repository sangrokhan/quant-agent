"""Strategy: SMA trend-following gated by a rolling Approximate Entropy (ApEn) regularity filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-047):
Approximate Entropy (Pincus 1991, https://en.wikipedia.org/wiki/Approximate_entropy)
measures how regular/predictable a short window of a time series is: low ApEn
means the recent return sequence is more pattern-like (trending/structured),
high ApEn means it is closer to noise. Trend-following signals (e.g. a simple
SMA-slope breakout) should have better edge specifically when the market's
recent return sequence is in a LOW-ApEn (more regular/structured) regime, and
should be actively harmful when ApEn is high (noisy chop -- whipsaws a naive
trend rule). This is a genuinely new indicator family for this repo (first
entropy-based construction; previously the repo used volatility-percentile
and Hurst-exponent-style regime gates, not information-theoretic regularity
measures) -- distinct from the volatility-regime gates used in
2026-09-03_bb_meanrev_qqq_volregime.py and the many "vol regime gate" near-miss
follow-ups, since ApEn is a regularity/predictability measure on returns
directly, not a magnitude-of-volatility measure.

Signal logic
------------
- Compute rolling ApEn(m=2, r=r_mult * rolling std of daily log returns) over
  a short window (entropy_window days) of daily log returns.
- "Low entropy regime" = current ApEn <= its trailing (entropy_lookback-day)
  median * entropy_regime_ratio.
- Entry (long): close > SMA(trend_window) (simple trend-following breakout)
  AND we are in a low-entropy regime.
- Exit: close crosses back below SMA(trend_window) (trend break), OR the
  entropy regime flips to high (risk-off exit -- signal that structure has
  broken down), OR after max_hold_days trading days (avoid indefinite holds).
- Flat (no position) whenever not in an active long.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _apen_vectorized(seg: np.ndarray, m: int, r: float) -> float:
    """Vectorized approximate entropy of a short 1-D segment (numpy, no python
    inner loop over N) -- uses sliding_window_view + broadcasting instead of
    the naive O(N^2) python-loop reference implementation, since this is
    recomputed at every rolling window position across the full price history."""
    n_total = len(seg)
    if n_total < m + 2 or r <= 0 or not np.isfinite(r):
        return np.nan

    def _phi(mm: int) -> float:
        n = n_total - mm + 1
        if n <= 0:
            return np.nan
        x = np.lib.stride_tricks.sliding_window_view(seg, mm)  # (n, mm)
        # pairwise Chebyshev distance via broadcasting: (n, n, mm) -> (n, n)
        diff = np.abs(x[:, None, :] - x[None, :, :]).max(axis=2)
        counts = (diff <= r).sum(axis=1) / n
        counts = np.where(counts <= 0, np.nan, counts)
        return np.nanmean(np.log(counts))

    phi_m = _phi(m)
    phi_m1 = _phi(m + 1)
    if not np.isfinite(phi_m) or not np.isfinite(phi_m1):
        return np.nan
    return phi_m - phi_m1


def _rolling_apen(returns: pd.Series, entropy_window: int, m: int, r_mult: float) -> pd.Series:
    vals = returns.values.astype(float)
    n = len(vals)
    out = np.full(n, np.nan)
    valid = ~np.isnan(vals)
    for end in range(entropy_window, n + 1):
        seg = vals[end - entropy_window : end]
        seg = seg[~np.isnan(seg)]
        if len(seg) < entropy_window * 0.8:
            continue
        r = r_mult * np.std(seg, ddof=0)
        out[end - 1] = _apen_vectorized(seg, m, r)
    return pd.Series(out, index=returns.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 20,
    entropy_window: int = 20,
    entropy_lookback: int = 126,
    entropy_regime_ratio: float = 1.0,
    r_mult: float = 0.2,
    m: int = 2,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)

    apen = _rolling_apen(daily_log_ret, entropy_window=entropy_window, m=m, r_mult=r_mult)
    apen_median = apen.rolling(entropy_lookback, min_periods=entropy_window).median()
    low_entropy_regime = apen <= (apen_median * entropy_regime_ratio)

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    entry = trend_up & low_entropy_regime.fillna(False)
    exit_trend_break = ~trend_up
    exit_regime_flip = ~low_entropy_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_break.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

"""Strategy: Ehlers AutoTune dominant-cycle bandpass filter, ROC zero-cross.

Hypothesis (see knowledge_base entry): per John F. Ehlers' TASC 5/2026
article, reproduced at
https://financial-hacker.com/the-autotune-filter/ (fully disclosed
EasyLanguage-to-C code): a highpassed price series' own autocorrelation
across a range of lags identifies the currently-dominant market cycle
(the lag with MINIMUM correlation, doubled, is the estimated cycle length
in bars). That estimate is fed as the center period of a 2-pole bandpass
filter. Entering/exiting on the 2-bar rate-of-change of the bandpass
output crossing zero -- but ONLY when the correlation minimum itself is
below a threshold (i.e. we are actually in a cyclic regime, not just
noise) -- should time cycle turns better than a fixed-period bandpass.

Algorithm (fully disclosed by source):
1. hp = HighPass3(close, window) -- reuse a 2-pole highpass building block
   (approximated here with the repo's existing 2-pole highpass filter).
2. For lag in 1..window: compute Pearson correlation of hp[t] vs
   hp[t-lag] over a rolling `window`-bar sample.
3. min_corr = min over lags of that correlation; dominant_cycle =
   2 * argmin_lag, smoothed/clamped to move at most +/-2 bars per bar.
4. bp = BandPass2(close, period=dominant_cycle, bandwidth) -- 2-pole
   bandpass filter centered on the dominant cycle.
5. roc = bp[t] - bp[t-2] (2-bar rate of change of the bandpass output).
6. Long when roc crosses from negative to positive AND min_corr < thresh
   (cyclic regime gate); exit on reverse cross or regime gate failing.

This is long-only (source's short-entry condition, mirrored with `Filt`
sign, is dropped for consistency with this repo's long-only convention).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _highpass2(series: pd.Series, length: int) -> pd.Series:
    """2-pole highpass filter (Ehlers standard building block)."""
    n = max(2, int(length))
    alpha = (np.cos(2 * np.pi / n) + np.sin(2 * np.pi / n) - 1) / np.cos(2 * np.pi / n)
    vals = series.to_numpy(dtype=float)
    out = np.zeros_like(vals)
    for i in range(len(vals)):
        v = vals[i]
        v1 = vals[i - 1] if i >= 1 else v
        v2 = vals[i - 2] if i >= 2 else v
        p1 = out[i - 1] if i >= 1 else 0.0
        p2 = out[i - 2] if i >= 2 else 0.0
        out[i] = ((1 - alpha / 2) ** 2) * (v - 2 * v1 + v2) + 2 * (1 - alpha) * p1 - ((1 - alpha) ** 2) * p2
    return pd.Series(out, index=series.index)


def _autotune_dominant_cycle(hp: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    """Returns (dominant_cycle_series, min_corr_series)."""
    vals = hp.to_numpy(dtype=float)
    n = len(vals)
    dc = np.full(n, float(window))
    min_corr = np.ones(n)

    for i in range(window * 2, n):
        window_x = vals[i - window:i]
        best_corr = 1.0
        best_lag = window
        for lag in range(1, window + 1):
            x = vals[i - window - lag: i - lag]
            y = window_x
            if len(x) != window or len(y) != window:
                continue
            sx, sy = x.sum(), y.sum()
            sxx, syy, sxy = (x * x).sum(), (y * y).sum(), (x * y).sum()
            den1 = window * sxx - sx * sx
            den2 = window * syy - sy * sy
            denom = np.sqrt(max(den1 * den2, 1e-12))
            corr = (window * sxy - sx * sy) / denom if denom > 0 else 0.0
            if corr < best_corr:
                best_corr = corr
                best_lag = lag
        candidate_dc = 2 * best_lag
        prev_dc = dc[i - 1]
        dc[i] = min(max(candidate_dc, prev_dc - 2), prev_dc + 2)
        min_corr[i] = best_corr

    return pd.Series(dc, index=hp.index), pd.Series(min_corr, index=hp.index)


def _bandpass2(price: pd.Series, period_series: pd.Series, bandwidth: float) -> pd.Series:
    vals = price.to_numpy(dtype=float)
    periods = period_series.to_numpy(dtype=float)
    n = len(vals)
    out = np.zeros(n)
    for i in range(n):
        period = max(periods[i], 3.0)
        l1 = np.cos(2.0 * np.pi / period)
        g1 = np.cos(bandwidth * 2.0 * np.pi / period)
        g1 = g1 if abs(g1) > 1e-6 else 1e-6
        inner = max(1.0 / (g1 * g1) - 1.0, 0.0)
        s1 = 1.0 / g1 - np.sqrt(inner)
        v0 = vals[i]
        v2 = vals[i - 2] if i >= 2 else v0
        bp1 = out[i - 1] if i >= 1 else 0.0
        bp2 = out[i - 2] if i >= 2 else 0.0
        out[i] = 0.5 * (1 - s1) * (v0 - v2) + l1 * (1 + s1) * bp1 - s1 * bp2
    return pd.Series(out, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 20,
    bandwidth: float = 0.25,
    corr_thresh: float = 0.3,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    hp = _highpass2(close, window)
    dc, min_corr = _autotune_dominant_cycle(hp, window)
    bp = _bandpass2(close, dc, bandwidth)
    roc = bp - bp.shift(2).fillna(0.0)

    cross_up = (roc.shift(1) <= 0) & (roc > 0)
    cross_down = (roc.shift(1) >= 0) & (roc < 0)
    cyclic_regime = min_corr < corr_thresh

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(cross_down.iloc[i]) or not bool(cyclic_regime.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]) and bool(cyclic_regime.iloc[i]):
                in_position = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

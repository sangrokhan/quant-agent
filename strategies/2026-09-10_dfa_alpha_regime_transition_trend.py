"""Strategy: Detrended Fluctuation Analysis (DFA) scaling-exponent regime
transition, gating a trend-following entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-XXX):
Per pyquantlab.com's "Detrended Fluctuation Analysis (DFA)" article
(visited this iteration,
https://www.pyquantlab.com/article.php?file=Detrended%20Fluctuation%20Analysis%20%28DFA%29.html),
DFA estimates a scaling exponent alpha from the log-log slope of the RMS
fluctuation function F(n) vs window size n, computed on the detrended
cumulative sum of returns. alpha < 0.5 = anti-persistent, alpha ~= 0.5 =
uncorrelated/random-walk, alpha > 0.5 = persistent (trends tend to
continue). The source's own worked BTC example found alpha=0.57
("persistent behavior... an upward movement tends to be followed by
further upward movements").

This is a DIFFERENT construction from this repo's two prior rejected
Hurst-exponent strategies (2026-09-04-155/156, which used classical R/S
rescaled-range analysis as a *continuous static-threshold gate* on an
EMA-crossover / z-score entry). DFA uses local-linear-detrending on
non-overlapping segments across a range of scales rather than R/S's
range/std ratio, and is known to behave differently on non-stationary
series (which daily equity/crypto prices are). Critically, this strategy
also differs behaviorally: instead of gating continuously on the raw level
of the persistence statistic (as both rejected Hurst attempts did), it
trades the *regime TRANSITION* -- the rolling DFA alpha crossing UP through
a threshold from below, i.e. the market just switched from a
noise/anti-persistent regime into a persistent-trending regime -- combined
with a broad SMA trend filter for direction. Exit occurs when alpha
crosses back down through the threshold (regime reverting to noise) or the
trend filter breaks, or after a time-stop.

Signal logic
------------
- log_ret = ln(close / close.shift(1))
- dfa_alpha[t] = DFA scaling exponent computed on the trailing dfa_window
  bars of log_ret ending at t (detrended-fluctuation log-log slope across
  a handful of scales in [scale_min, scale_max]).
- alpha_up_cross[t] = dfa_alpha[t-1] < dfa_threshold AND dfa_alpha[t] >= dfa_threshold
  (regime just turned persistent).
- trend_up = close > close.rolling(trend_window).mean()
- Entry (long): alpha_up_cross AND trend_up.
- Exit: dfa_alpha crosses back below dfa_threshold, OR trend_up flips
  False, OR held >= max_hold_days.

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


def _dfa_alpha_single(x: np.ndarray, scales) -> float:
    """Compute the DFA scaling exponent for one 1-D array of returns."""
    x = x[~np.isnan(x)]
    if len(x) < max(scales) * 2:
        return np.nan
    y = np.cumsum(x - np.mean(x))
    fluct = np.zeros(len(scales))
    for i, scale in enumerate(scales):
        n_seg = len(y) // scale
        if n_seg < 2:
            fluct[i] = np.nan
            continue
        shape = (n_seg, scale)
        seg = y[: n_seg * scale].reshape(shape)
        scale_ax = np.arange(scale)
        rms_vals = np.empty(n_seg)
        for j in range(n_seg):
            coeff = np.polyfit(scale_ax, seg[j], 1)
            fit = np.polyval(coeff, scale_ax)
            rms_vals[j] = np.sqrt(np.mean((seg[j] - fit) ** 2))
        fluct[i] = np.sqrt(np.mean(rms_vals ** 2))
    valid = ~np.isnan(fluct) & (fluct > 0)
    if valid.sum() < 3:
        return np.nan
    coeff = np.polyfit(np.log2(np.array(scales)[valid]), np.log2(fluct[valid]), 1)
    return float(coeff[0])


def _rolling_dfa_alpha(log_ret: pd.Series, dfa_window: int, scale_min: int, scale_max: int, n_scales: int) -> pd.Series:
    scales = sorted(set(np.linspace(scale_min, scale_max, n_scales).astype(int)))
    arr = log_ret.values.astype(float)
    out = np.full(len(arr), np.nan)
    for i in range(dfa_window, len(arr) + 1):
        window = arr[i - dfa_window : i]
        out[i - 1] = _dfa_alpha_single(window, scales)
    return pd.Series(out, index=log_ret.index)


def generate_signals(
    price_df: pd.DataFrame,
    dfa_window: int = 100,
    dfa_threshold: float = 0.55,
    trend_window: int = 100,
    max_hold_days: int = 20,
    scale_min: int = 5,
    scale_max: int = 20,
    n_scales: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ratios = close / close.shift(1)
    log_ret = np.log(ratios.where(ratios > 0))

    dfa_alpha = _rolling_dfa_alpha(log_ret, dfa_window, scale_min, scale_max, n_scales)

    prev_alpha = dfa_alpha.shift(1)
    alpha_up_cross = (prev_alpha < dfa_threshold) & (dfa_alpha >= dfa_threshold)
    alpha_down_cross = (prev_alpha >= dfa_threshold) & (dfa_alpha < dfa_threshold)

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    entry = alpha_up_cross.fillna(False) & trend_up.fillna(False)
    exit_condition = alpha_down_cross.fillna(False) | (~trend_up.fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_condition.iloc[i]) or held >= max_hold_days:
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

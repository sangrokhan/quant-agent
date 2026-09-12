"""Strategy: Ehlers AutoTune Filter -- dominant-cycle bandpass, long-only, cyclic-regime gated.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per John Ehlers' TASC 5/2026 article "A Rolling Autocorrelation Function",
transcribed with full C/EasyLanguage-derived formula at
https://financial-hacker.com/the-autotune-filter/ (Petra Volkova):
markets periodically exhibit a dominant price cycle detectable via rolling
autocorrelation of a highpass-filtered series -- the lag with the MOST
NEGATIVE (anticorrelated) autocorrelation, doubled, estimates the dominant
cycle length. Tuning a bandpass filter to that dynamically-estimated cycle
and trading its rate-of-change (ROC) zero-crossings, gated by a
minimum-correlation threshold (confirms a genuinely cyclic regime is
present rather than trading noise), should outperform an untuned/fixed-
period oscillator, per the source's own reported ~25% CAGR vs buy-and-hold
on ES futures (with an important caveat raised in the source's own comment
thread: a shuffled-control reanalysis found no significant cyclic
structure survives in real FX/index return data at that scale -- this
strategy is tested here on equity/crypto daily bars specifically to check
whether the same caveat holds).

Signal logic
------------
- AutoTune(close, window): 2-pole highpass filter over `window` bars, then
  rolling autocorrelation across lags 1..window; dominant cycle DC = 2 *
  argmin(corr), clamped to the prior DC +/- 2 bars (recursion approximated
  here with a simple bar-to-bar clamp on a rolling basis).
- BandPass2(close, DC, bandwidth): 2nd-order bandpass filter tuned to DC.
- Long entry (long-only adaptation of source's long/short rule): 2-bar ROC
  of the bandpass output crosses from negative/zero to positive AND the
  regime's min-correlation (MinCorr, the most negative correlation found)
  is below `corr_thresh` (confirms cyclic regime).
- Exit: ROC crosses back to non-positive, OR a `max_hold_days` time-stop
  (source's original doesn't specify an explicit hold cap; added here to
  avoid indefinite holds through a walk-forward/grid harness).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _highpass2(price: np.ndarray, period: int) -> np.ndarray:
    """2-pole highpass filter (Ehlers standard coefficients)."""
    n = len(price)
    out = np.zeros(n)
    a1 = np.exp(-1.414 * np.pi / period)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = (1 + c2 - c3) / 4.0
    for i in range(2, n):
        out[i] = (
            c1 * (price[i] - 2 * price[i - 1] + price[i - 2])
            + c2 * out[i - 1]
            + c3 * out[i - 2]
        )
    return out


def _autotune_dc_series(hp: np.ndarray, window: int) -> tuple:
    """Vectorized per-bar dominant-cycle + min-correlation series.

    For each bar i, uses the trailing `2*window` highpassed samples: a fixed
    base segment `xw` (first `window` samples) and, for each lag 1..window,
    a shifted segment `yw` (samples `lag..lag+window`) drawn from the SAME
    2*window historical span -- matching the source's HP[J] vs HP[Lag+J]
    correlation over one window. The lag with the most-negative correlation
    (anticorrelation), doubled, is the dominant-cycle estimate, clamped to
    the prior estimate +/- 2 bars (the source's own recursive clamp).
    """
    n = len(hp)
    dc_series = np.full(n, float(window))
    min_corr_series = np.ones(n)
    if n < 2 * window:
        return dc_series, min_corr_series

    lags = np.arange(1, window + 1)
    prev_dc = float(window)
    for i in range(2 * window - 1, n):
        base = hp[i - 2 * window + 1 : i + 1]  # length 2*window
        xw = base[:window]
        sx = xw.sum()
        sxx = (xw * xw).sum()
        # Build a (window, window) matrix of shifted windows for all lags at once.
        Y = np.lib.stride_tricks.sliding_window_view(base[1:], window)[: window]
        sy = Y.sum(axis=1)
        syy = (Y * Y).sum(axis=1)
        sxy = (Y * xw).sum(axis=1)
        den1 = window * sxx - sx * sx
        den2 = window * syy - sy * sy
        denom = den1 * den2
        with np.errstate(invalid="ignore", divide="ignore"):
            corr = np.where(denom > 0, (window * sxy - sx * sy) / np.sqrt(np.where(denom > 0, denom, 1.0)), 1.0)
        best_idx = int(np.argmin(corr))
        best_lag = lags[best_idx]
        best_corr = float(corr[best_idx])
        dc = 2.0 * best_lag
        dc = float(np.clip(dc, prev_dc - 2.0, prev_dc + 2.0))
        dc_series[i] = dc
        min_corr_series[i] = best_corr
        prev_dc = dc
    return dc_series, min_corr_series


def _bandpass2(price: np.ndarray, dc_series: np.ndarray, bandwidth: float) -> np.ndarray:
    n = len(price)
    out = np.zeros(n)
    for i in range(2, n):
        period = max(dc_series[i], 3.0)
        l1 = np.cos(2.0 * np.pi / period)
        g1 = np.cos(bandwidth * 2.0 * np.pi / period)
        denom = g1 if g1 != 0 else 1e-6
        inner = 1.0 / (denom * denom) - 1.0
        s1 = 1.0 / denom - np.sqrt(max(inner, 0.0))
        out[i] = (
            0.5 * (1.0 - s1) * (price[i] - price[i - 2])
            + l1 * (1.0 + s1) * out[i - 1]
            - s1 * out[i - 2]
        )
    return out


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 20,
    bandwidth: float = 0.25,
    corr_thresh: float = -0.2,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    price = close.to_numpy(dtype=float)
    n = len(price)

    hp = _highpass2(price, window)
    dc_series, min_corr_series = _autotune_dc_series(hp, window)

    bp = _bandpass2(price, dc_series, bandwidth)
    roc = np.zeros(n)
    roc[2:] = bp[2:] - bp[:-2]

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(1, n):
        cross_up = roc[i - 1] <= 0 and roc[i] > 0
        cross_down = roc[i - 1] > 0 and roc[i] <= 0
        cyclic_regime = min_corr_series[i] < corr_thresh
        if in_position:
            held = i - entry_idx
            if cross_down or held >= max_hold_days:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if cross_up and cyclic_regime:
                in_position = True
                entry_idx = i
                position[i] = 1
            else:
                position[i] = 0
    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

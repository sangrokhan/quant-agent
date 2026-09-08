"""Strategy: Savitzky-Golay-Smoothed Trend Filter (edge-preserving momentum).

Hypothesis (see knowledge_base/strategies_log.jsonl, this id):
Per Marc Weibel, "Edge-Preserving Macro-Financial Signal Extraction for
Real-Time U.S. Sector Rotation" (2026), summarized in Quantitativo Weekly
#3 (https://www.quantitativo.com/p/quantitativo-weekly-3): applying a
one-sided, edge-preserving smoothing filter to a raw trading signal before
using it (vs. trading the raw/unsmoothed signal directly) roughly triples
Sharpe (0.304 raw -> 0.707 with a Savitzky-Golay smoother, 0.820 with a
more exotic anisotropic-diffusion filter) in the source's sector-rotation
backtest, because edge-preserving filters "smooth inside a regime but keep
the jumps between regimes" -- this materially cuts turnover/whipsaw (8.2x
-> 4.4x annual turnover in the source) without lagging real regime changes
away.

This repo has no macro/VIX/sector-ratio dataset matching the source's exact
4-signal setup, so we adapt the core, portable finding -- "smooth the
trading signal itself with a one-sided causal Savitzky-Golay filter before
thresholding it, rather than trading the raw signal" -- to this repo's
simplest available trend proxy: a moving-average-crossover-style momentum
score (price minus its own SMA, normalized), smoothed causally with a
one-sided Savitzky-Golay filter (applied only to already-elapsed data at
each point, no lookahead) before the long/flat threshold is applied.

Distinct from every prior SMA/EMA/KAMA-crossover trend entry in this repo:
none of them apply a Savitzky-Golay (polynomial local-regression) smoother
to the signal itself -- they use raw SMA/EMA crossovers or KAMA's adaptive
smoothing constant, not a fixed-order polynomial edge-preserving filter
applied to a momentum score.

Signal logic
------------
- Raw momentum score: raw(t) = close[t] / SMA(sma_window)[t] - 1.
- Causal Savitzky-Golay smoothing: at each t, fit a `polyorder`-degree
  polynomial to the trailing `sg_window` raw(t) values (one-sided/causal --
  only past+current data used, replicating the source's "real-time,
  one-sided filter" requirement) and take the fitted value at the most
  recent point as the smoothed signal smooth(t).
- Position = 1 (long) when smooth(t) > 0, else 0 (flat).
- Lagged 1 day.

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


def _causal_savgol(values: np.ndarray, sg_window: int, polyorder: int) -> np.ndarray:
    """One-sided (causal) Savitzky-Golay smoothing: at each index i, fit a
    `polyorder`-degree polynomial to the trailing `sg_window` values (only
    past+current data -- no future data used at any i) and take the FITTED
    VALUE AT THE LAST (most recent) POINT of that window.

    Vectorized via `scipy.signal.savgol_coeffs(pos=window-1)`: this returns
    the fixed FIR coefficients that, convolved with a trailing window,
    directly give the polynomial fit evaluated at the window's last point
    (the one-sided/causal case) -- computed once, then applied to the whole
    series via `np.convolve`, rather than re-fitting per index.
    """
    from scipy.signal import savgol_coeffs

    n = len(values)
    if sg_window % 2 == 0:
        sg_window += 1
    polyorder = min(polyorder, sg_window - 1)
    if n < sg_window:
        return np.full(n, np.nan)

    # coefficients for evaluating the causal (one-sided, pos=window-1) fit
    coeffs = savgol_coeffs(sg_window, polyorder, pos=sg_window - 1)
    # np.convolve with 'valid' mode gives, at output index j, the fitted
    # value using values[j : j+sg_window] -- align so it lines up with the
    # window's LAST index (j + sg_window - 1) in the original series.
    filled = np.nan_to_num(values, nan=0.0)
    valid_mask = (~np.isnan(values)).astype(float)
    conv = np.convolve(filled, coeffs[::-1], mode="valid")
    out = np.full(n, np.nan)
    out[sg_window - 1 :] = conv
    # blank out any window that contained a NaN input (rolling sum of the mask)
    mask_conv = np.convolve(valid_mask, np.ones(sg_window), mode="valid")
    invalid = mask_conv < sg_window
    out[sg_window - 1 :][invalid] = np.nan
    return out


def _simulate(
    price_df: pd.DataFrame,
    sma_window: int = 50,
    sg_window: int = 21,
    polyorder: int = 2,
) -> pd.DataFrame:
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(sma_window, min_periods=sma_window // 2).mean()
    raw_score = (close / sma - 1.0).to_numpy(dtype=float)

    smooth_vals = _causal_savgol(raw_score, sg_window, polyorder)
    smooth_score = pd.Series(smooth_vals, index=close.index)

    raw_signal = (smooth_score > 0).fillna(False).astype(int)
    position = raw_signal.shift(1).fillna(0).astype(int)

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position * daily_ret

    return pd.DataFrame({"position": position, "returns": strat_ret}, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 50,
    sg_window: int = 21,
    polyorder: int = 2,
) -> pd.Series:
    result = _simulate(price_df, sma_window, sg_window, polyorder)
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    sma_window: int = 50,
    sg_window: int = 21,
    polyorder: int = 2,
) -> pd.Series:
    result = _simulate(price_df, sma_window, sg_window, polyorder)
    return result["returns"]

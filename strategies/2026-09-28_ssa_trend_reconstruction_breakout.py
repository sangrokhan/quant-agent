"""Strategy: Singular Spectrum Analysis (SSA) rolling trend-reconstruction
crossover, long-only.

Hypothesis (source: https://en.wikipedia.org/wiki/Singular_spectrum_analysis,
read this iteration via browser_exec after web_extract's ddgs backend refused
extraction -- "Methodology"/"Decomposition and reconstruction" sections, and
independently cross-checked against arXiv:0804.3367 "A Method Of Trend
Extraction Using Singular Spectrum Analysis"):

SSA embeds a length-N price window into an L x K trajectory (Hankel) matrix
D (L=embedding dimension, K=N-L+1, each column a length-L lagged slice of
the series), then takes its SVD D = U S V'. The leading r singular
components (largest singular values) capture the slow, low-frequency
"trend" component of the series (Karhunen-Loeve / PCA-in-the-time-domain
decomposition); the remaining components capture oscillatory/noise
structure. Reconstructing the series from only the top r components and
anti-diagonal-averaging (Hankelization) recovers a smoothed trend estimate
at every point in the window.

This repo has one PRIOR SSA-adjacent entry (2026-09-24-006, "no_candidate"):
that iteration found only a purely THEORETICAL MQL5 writeup with no
disclosed mechanical entry/exit rule and dead-ended. This iteration
resolves that gap: the exact reconstruction math above is fully disclosed
and mechanical (matrix embedding -> SVD -> low-rank truncation ->
anti-diagonal averaging), not paywalled or hand-wavy, so it is implemented
here from first principles (via numpy.linalg.svd, no smoothing library).

Key efficiency trick used here (avoids O(N) anti-diagonal-averaging passes
per bar): the LAST reconstructed value of a length-N trailing window sits
at the trajectory matrix's bottom-right CORNER cell (row L-1, col K-1 in
0-indexed terms), which is the unique element on that anti-diagonal (i+j is
maximal there) -- so it needs no averaging, just a direct low-rank corner
readout at every rolling step. This makes a rolling/causal (no lookahead)
SSA trend line tractable to compute bar-by-bar on daily data.

Signal logic:
- At each bar t (once at least `window_len` bars of history exist), take
  the trailing `window_len`-bar close-price window, build its L x K
  trajectory matrix (L=`embed_dim`), SVD it, and read off the corner-cell
  value reconstructed from the top `n_components` singular triples. This
  is `ssa_trend[t]` -- a smoothed, causal (only uses data up to and
  including bar t) trend estimate of the closing price at bar t.
- Long entry: ssa_trend has turned from flat/falling to rising (its own
  `slope_lookback`-bar slope turns positive) AND close[t] is above
  ssa_trend[t] (price confirms the trend read, avoiding whipsaw off a
  reconstruction blip alone).
- Exit: ssa_trend's slope turns non-positive, OR close falls below
  ssa_trend, OR a max_hold_days time-stop -- whichever comes first.

Distinct from this repo's many other trend-smoother strategies (Ehlers
SuperSmoother/Roofing Filter/FRAMA, McGinley Dynamic, ALMA, KAMA, VIDYA,
wavelet-denoised trend) via its data-adaptive spectral (SVD/eigenvalue)
construction rather than a fixed-form recursive filter or adaptive-alpha
EMA -- SSA's basis functions are derived from the data itself (Karhunen-
Loeve), not a predetermined kernel.

Interface contract (see validation/validators.py and validation/grid_test.py):
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


def _ssa_trend_series(
    close: pd.Series,
    window_len: int,
    embed_dim: int,
    n_components: int,
) -> np.ndarray:
    """Rolling causal SSA trend estimate: for each bar t >= window_len-1,
    reconstruct the trailing window's trend value at its LAST point (the
    trajectory matrix's corner cell, needing no anti-diagonal averaging)
    from the top `n_components` singular triples. Returns a NaN-padded
    array aligned with `close`.
    """
    values = close.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan, dtype=float)

    L = embed_dim
    K = window_len - L + 1
    if K < L:
        # Degenerate embedding (L too large relative to window) -- swap so
        # L <= K, standard SSA convention, keeps the trajectory matrix tall.
        L, K = K, L

    r = max(1, min(n_components, L))

    for t in range(window_len - 1, n):
        w = values[t - window_len + 1 : t + 1]
        # Build L x K trajectory (Hankel) matrix.
        traj = np.empty((L, K))
        for j in range(K):
            traj[:, j] = w[j : j + L]
        try:
            u, s, vt = np.linalg.svd(traj, full_matrices=False)
        except np.linalg.LinAlgError:
            continue
        rr = min(r, len(s))
        # Corner cell (L-1, K-1) reconstructed from the top rr components --
        # unique element on its anti-diagonal, so no averaging needed.
        corner = 0.0
        for k in range(rr):
            corner += s[k] * u[L - 1, k] * vt[k, K - 1]
        out[t] = corner

    return out


def generate_signals(
    price_df: pd.DataFrame,
    window_len: int = 60,
    embed_dim: int = 15,
    n_components: int = 2,
    slope_lookback: int = 3,
    max_hold_days: int = 30,
    min_hold_days: int = 5,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    ``min_hold_days`` suppresses the slope/price-position exit conditions
    for the first N bars after entry (this repo's established transaction-
    cost-survival fix pattern -- first used for the Klinger Volume
    Oscillator near-miss 2026-09-04-085 -- since the raw per-bar SSA-slope
    reconstruction flips direction often enough on its own that an
    unmodified crossover trades far too frequently to survive costs). The
    time-stop (max_hold_days) remains active immediately regardless.
    """
    df = _prep(price_df)
    close = df["close"]

    ssa = _ssa_trend_series(close, window_len, embed_dim, n_components)
    ssa_series = pd.Series(ssa, index=df.index)
    slope = ssa_series.diff(slope_lookback)

    close_arr = close.to_numpy()
    ssa_arr = ssa_series.to_numpy()
    slope_arr = slope.to_numpy()
    n = len(df)

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if np.isnan(ssa_arr[i]) or np.isnan(slope_arr[i]):
            continue
        rising = slope_arr[i] > 0
        above = close_arr[i] > ssa_arr[i]
        if in_pos:
            hold_count += 1
            time_stop = hold_count >= max_hold_days
            crossover_exit = (hold_count >= min_hold_days) and ((not rising) or (not above))
            exit_now = time_stop or crossover_exit
            if exit_now:
                in_pos = False
                hold_count = 0
            else:
                pos.iloc[i] = 1.0
        if not in_pos and rising and above:
            in_pos = True
            hold_count = 0
            pos.iloc[i] = 1.0

    return pos * leverage_cap


def generate_returns(
    price_df: pd.DataFrame,
    window_len: int = 60,
    embed_dim: int = 15,
    n_components: int = 2,
    slope_lookback: int = 3,
    max_hold_days: int = 30,
    min_hold_days: int = 5,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        window_len=window_len,
        embed_dim=embed_dim,
        n_components=n_components,
        slope_lookback=slope_lookback,
        max_hold_days=max_hold_days,
        min_hold_days=min_hold_days,
        leverage_cap=leverage_cap,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret

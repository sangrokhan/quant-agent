"""Strategy: Chaos-to-Order regime TRANSITION trigger (Lyapunov exponent
crossing below threshold + low Grassberger-Procaccia correlation dimension)
combined with an SMA trend filter, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl, this entry's id):
Per PyQuantLab's "A Chaos Theory-Based Trading Strategy in Backtrader"
(Medium, Jun 2025, https://pyquantlab.medium.com/a-chaos-theory-based-trading-strategy-in-backtrader-46bde42bdcb6,
read via browser_exec after web_search's DDGS backend TLS-erroring on the
correlation-dimension follow-up query, full disclosed backtrader source
code): the strategy enters ONLY on the specific TRANSITION event where the
rolling largest Lyapunov exponent estimate crosses DOWN through
lyap_threshold (chaotic -> ordered regime change, not merely "currently
below threshold") AND the rolling Grassberger-Procaccia correlation
dimension is below corr_dim_threshold (simple/low-complexity attractor
structure), gated by a simple SMA trend filter for direction. Exit when the
Lyapunov exponent rises back above 2x lyap_threshold ("chaos resuming").

This is distinct from this repo's prior Lyapunov-Hurst strategy
(2026-09-20-150, accepted QQQ) in two ways disclosed explicitly in the
source: (1) it triggers on the TRANSITION/crossing event itself, not a
persistent-state gate every bar the condition holds; (2) it substitutes
Grassberger-Procaccia correlation dimension (a fractal-dimension complexity
measure of the phase-space attractor) for the Hurst-persistence filter used
previously. First correlation-dimension-based strategy in this repo (0
prior "correlation dimension"/"grassberger" hits).

Implementation notes: the source's own Lyapunov/correlation-dimension
routines are reused near-verbatim (single-reference-lag Rosenstein-style
Lyapunov re-used from this repo's own prior implementation for consistency;
Grassberger-Procaccia correlation dimension implemented per the source's
own disclosed pdist/logspace/linregress recipe). Long-only adaptation of
the source's long/short backtrader strategy (repo convention, matching
other strategies' 0/1 position contract).

Signal logic
------------
- Largest Lyapunov exponent: same simplified Rosenstein-style rolling
  estimate as 2026-09-20-150 (embed_dim=2, temporal near-neighbor
  exclusion, single divergence horizon) on log returns.
- Correlation dimension (Grassberger-Procaccia): embed the rolling log-
  return window into `embedding_dim`-dim phase space (delay=1), compute all
  pairwise distances, build the correlation integral C(r) over 10
  log-spaced radii between min/max nonzero distance, and take the
  linear-regression slope of log(C(r)) vs log(r) as the dimension estimate
  (bounded to [0, embedding_dim]).
- Entry (long): Lyapunov exponent crosses DOWN through lyap_threshold this
  bar (was >= threshold last bar, now < threshold) AND correlation
  dimension < corr_dim_threshold AND close > SMA(trend_window) (uptrend).
- Exit: Lyapunov exponent rises above 2 * lyap_threshold ("chaos
  resuming", the source's own exit condition), OR close crosses back below
  SMA(trend_window), OR max_hold_days elapses (safety backstop).

Interface contract (see validation/validators.py, validation/grid_test.py):
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


def _rolling_lyapunov(
    log_ret: pd.Series,
    window: int,
    embed_dim: int = 2,
    min_sep: int = 5,
    horizon: int = 4,
) -> pd.Series:
    """Simplified Rosenstein-style largest Lyapunov exponent estimate,
    rolling window (same construction as 2026-09-20-150)."""
    vals = log_ret.values
    n = len(vals)
    out = np.full(n, np.nan)

    for end in range(window, n):
        w = vals[end - window : end]
        m = embed_dim
        wl = len(w)
        n_pts = wl - (m - 1) - horizon
        if n_pts < min_sep + 2:
            out[end] = np.nan
            continue
        emb = np.column_stack([w[i : i + n_pts] for i in range(m)])
        diffs = emb[:, None, :] - emb[None, :, :]
        dists = np.sqrt((diffs**2).sum(axis=2))
        idx = np.arange(n_pts)
        temporal_mask = np.abs(idx[:, None] - idx[None, :]) < min_sep
        dists_masked = np.where(temporal_mask, np.inf, dists)
        nn_idx = np.argmin(dists_masked, axis=1)
        d0 = dists_masked[idx, nn_idx]
        valid = np.isfinite(d0) & (d0 > 0)
        if valid.sum() < 5:
            out[end] = np.nan
            continue
        end_idx = idx + horizon
        nn_end_idx = nn_idx + horizon
        ok = valid & (end_idx < n_pts) & (nn_end_idx < n_pts)
        if ok.sum() < 5:
            out[end] = np.nan
            continue
        d_h = np.sqrt(((emb[end_idx[ok]] - emb[nn_end_idx[ok]]) ** 2).sum(axis=1))
        d0_ok = d0[ok]
        ratio = np.maximum(d_h / np.maximum(d0_ok, 1e-12), 1e-12)
        out[end] = np.mean(np.log(ratio)) / horizon

    return pd.Series(out, index=log_ret.index)


def _correlation_dimension(embedded: np.ndarray, embed_dim: int) -> float:
    """Grassberger-Procaccia correlation dimension estimate for one window's
    embedded vectors, per the source's own disclosed recipe."""
    n_pts = embedded.shape[0]
    if n_pts < 20:
        return 0.0
    try:
        diffs = embedded[:, None, :] - embedded[None, :, :]
        dist_matrix = np.sqrt((diffs**2).sum(axis=2))
        iu = np.triu_indices(n_pts, k=1)
        distances = dist_matrix[iu]
        if len(distances) == 0 or np.all(distances == 0):
            return 0.0
        nonzero = distances[distances > 0]
        if len(nonzero) == 0:
            return 0.0
        min_dist = nonzero.min()
        max_dist = distances.max()
        if min_dist >= max_dist:
            return 0.0
        radii = np.logspace(np.log10(min_dist), np.log10(max_dist), 10)
        correlation_integrals = np.array(
            [np.sum(distances < r) / len(distances) for r in radii]
        )
        valid_r = radii > 0
        log_radii = np.log(radii[valid_r])
        log_integrals = np.log(correlation_integrals[valid_r] + 1e-10)
        if len(log_radii) > 3:
            slope = np.polyfit(log_radii, log_integrals, 1)[0]
            return float(max(0.0, min(embed_dim, slope)))
        return 0.0
    except Exception:
        return 0.0


def _rolling_correlation_dimension(
    log_ret: pd.Series, window: int, embed_dim: int = 2, delay: int = 1
) -> pd.Series:
    vals = log_ret.values
    n = len(vals)
    out = np.full(n, np.nan)
    for end in range(window, n):
        w = vals[end - window : end]
        n_pts = len(w) - (embed_dim - 1) * delay
        if n_pts < 20:
            out[end] = 0.0
            continue
        emb = np.column_stack([w[i * delay : i * delay + n_pts] for i in range(embed_dim)])
        out[end] = _correlation_dimension(emb, embed_dim)
    return pd.Series(out, index=log_ret.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    lyap_window: int = 60,
    lyap_threshold: float = 0.42,
    corr_dim_window: int = 60,
    corr_dim_threshold: float = 1.5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    log_ret = np.log(close / close.shift(1)).fillna(0.0)

    sma = close.rolling(trend_window).mean()
    lyap = _rolling_lyapunov(log_ret, lyap_window)
    corr_dim = _rolling_correlation_dimension(log_ret, corr_dim_window)

    lyap_prev = lyap.shift(1)
    became_ordered = (lyap < lyap_threshold) & (lyap_prev >= lyap_threshold)
    simple_structure = corr_dim < corr_dim_threshold
    trend_ok = close > sma

    entry = became_ordered & simple_structure & trend_ok
    chaos_resuming = lyap > (lyap_threshold * 2)
    exit_signal = chaos_resuming | (~trend_ok)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_arr = entry.fillna(False).values
    exit_arr = exit_signal.fillna(True).values
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_arr[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_arr[i]):
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

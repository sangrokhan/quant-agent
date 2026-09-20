"""Strategy: Rolling largest-Lyapunov-exponent + Hurst-exponent regime filter
gating a simple SMA trend-following entry.

Hypothesis (see knowledge_base/strategies_log.jsonl, this entry's id):
Per PyQuantLab's "A Lyapunov-Hurst Regime Trading Strategy" (Medium, Nov 2025,
https://pyquantlab.medium.com/a-lyapunov-hurst-regime-trading-strategy-5214b89064e6,
read via browser_exec after web_search's DDGS backend TLS-erroring on the
detailed-formula follow-up query): financial markets alternate between
chaotic phases (price trajectories diverge rapidly -- high largest Lyapunov
exponent) and ordered/trending phases (Lyapunov exponent declines,
correlation dimension compresses -- more deterministic dynamics). The
source combines these "chaos metrics" with a trend filter and the Hurst
exponent (>0.5 = persistent/trending, <0.5 = mean-reverting) to trade the
transition INTO ordered regimes, aiming to capture trendable structure
rather than react to noise.

This is the first Lyapunov-exponent-based strategy in this repo (0 prior
"lyapunov" hits in strategies_index.jsonl) -- distinct from the 20+ prior
plain Hurst-exponent entries because it adds a genuinely new regime filter
(divergence-rate-of-nearby-return-trajectories) on top of the already-tried
Hurst persistence filter, rather than reusing Hurst alone.

Implementation notes (the source article did not disclose exact numeric
thresholds/window lengths, only the general chaos-metric + trend + Hurst
architecture, so parameters here are this iteration's own reasonable
starting values, kept explicit and tunable via the grid test):

- Largest Lyapunov exponent (Rosenstein et al. 1993, simplified, single
  reference lag k=1): for each rolling window of `lyap_window` daily log
  returns, embed into an m=2, tau=1 phase space, find each point's nearest
  neighbor (excluding temporally-adjacent points within `lyap_min_sep` bars
  to avoid trivial autocorrelation matches), track how fast the distance
  between a point and its nearest neighbor grows over `lyap_horizon` steps,
  and average the per-step log-growth rate across all valid pairs in the
  window. A LOW value indicates trajectories stay close together (orderly,
  more deterministic); a HIGH value indicates rapid divergence (chaotic).
- Hurst exponent: classic rescaled-range (R/S) estimate over a rolling
  window of `hurst_window` log returns.
- Entry (long): close > SMA(trend_window) (uptrend) AND rolling Lyapunov
  exponent < lyap_threshold (orderly/stabilizing regime) AND rolling Hurst
  > hurst_threshold (persistent/trending regime).
- Exit: close crosses back below SMA(trend_window), OR Lyapunov exponent
  rises back above lyap_threshold (regime turning chaotic again), OR Hurst
  drops back to/below hurst_threshold, OR max_hold_days elapses (safety
  backstop).

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


def _rolling_hurst(log_ret: pd.Series, window: int) -> pd.Series:
    """Classic rescaled-range (R/S) Hurst exponent, rolling window."""
    vals = log_ret.values
    n = len(vals)
    out = np.full(n, np.nan)
    for i in range(window, n):
        w = vals[i - window : i]
        mean = w.mean()
        dev = np.cumsum(w - mean)
        r = dev.max() - dev.min()
        s = w.std()
        if s <= 0 or r <= 0:
            out[i] = 0.5
            continue
        rs = r / s
        # H = log(R/S) / log(window)
        out[i] = np.log(rs) / np.log(window)
    return pd.Series(out, index=log_ret.index)


def _rolling_lyapunov(
    log_ret: pd.Series,
    window: int,
    embed_dim: int = 2,
    min_sep: int = 5,
    horizon: int = 4,
) -> pd.Series:
    """Simplified Rosenstein-style largest Lyapunov exponent estimate,
    rolling window, embed_dim=2 (tau=1), single divergence horizon.

    For each rolling window of returns, embed into an m-dim phase space,
    find each point's nearest neighbor at least `min_sep` bars away
    (temporal), then average the per-step log-growth of the
    initially-nearest-neighbor distance over `horizon` steps forward.
    """
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
        # embed
        emb = np.column_stack([w[i : i + n_pts] for i in range(m)])
        # pairwise distances among embedded points (excluding temporal
        # near neighbors)
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
        # forward distance after `horizon` steps
        end_idx = idx + horizon
        nn_end_idx = nn_idx + horizon
        ok = valid & (end_idx < n_pts) & (nn_end_idx < n_pts)
        if ok.sum() < 5:
            out[end] = np.nan
            continue
        d_h = np.sqrt(((emb[end_idx[ok]] - emb[nn_end_idx[ok]]) ** 2).sum(axis=1))
        d0_ok = d0[ok]
        ratio = d_h / np.maximum(d0_ok, 1e-12)
        ratio = np.maximum(ratio, 1e-12)
        lyap_est = np.mean(np.log(ratio)) / horizon
        out[end] = lyap_est

    return pd.Series(out, index=log_ret.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    lyap_window: int = 60,
    lyap_threshold: float = 0.42,
    hurst_window: int = 60,
    hurst_threshold: float = 0.5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    log_ret = np.log(close / close.shift(1)).fillna(0.0)

    sma = close.rolling(trend_window).mean()
    hurst = _rolling_hurst(log_ret, hurst_window)
    lyap = _rolling_lyapunov(log_ret, lyap_window)

    trend_ok = close > sma
    order_ok = lyap < lyap_threshold
    persist_ok = hurst > hurst_threshold

    entry = trend_ok & order_ok & persist_ok
    exit_signal = (~trend_ok) | (~order_ok) | (~persist_ok)

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

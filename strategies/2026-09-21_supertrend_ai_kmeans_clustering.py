"""Strategy: SuperTrend AI (K-Means Clustering), LuxAlgo.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://www.luxalgo.com/library/indicator/supertrend-ai-clustering
(published Aug 2023, mechanism read via browser_exec fallback -- web_search
DDGS returned no results for the direct query): LuxAlgo's "SuperTrend AI
(Clustering)" indicator evaluates a whole range of classic ATR-multiplier
SuperTrend "factor" values simultaneously, scores each factor's recent
trailing-stop performance (a running sum of "did price move in the direction
this factor's trailing stop implies" over a performance-memory window), then
applies k-means clustering (k=3: below-average/average/exceptional) to that
set of performance scores and picks the SuperTrend line whose factor belongs
to the chosen cluster (source's default = "best"/exceptional cluster) as the
live trailing stop. The claimed edge: instead of hand-picking one fixed ATR
multiplier, the indicator adaptively re-selects whichever factor is
*currently* producing the strongest trend-following performance, every bar.

This is a genuinely novel technique in this repo's knowledge base (no prior
k-means/adaptive-factor-selection SuperTrend entries) -- distinct from every
existing single-fixed-factor Chandelier/Supertrend/ATR-trailing-stop
strategy already tested here.

Signal logic (causal, no look-ahead)
-------------------------------------
1. For a small grid of ATR factors in [factor_min, factor_max] with a fixed
   step, compute the classic SuperTrend trailing-stop line + direction for
   each factor (upper/lower bands built from ATR(atr_length), direction
   flips when close crosses the opposite band).
2. For each factor, maintain a running "performance" score: each bar,
   perf += sign(close[t] - close[t-1]) * direction[t-1] , exponentially
   decayed by performance_memory (per LuxAlgo's own disclosed
   "Performance Memory" parameter -- higher = more weight on long-run
   history). This rewards factors whose SuperTrend direction agreed with
   that bar's actual price move.
3. At each bar, k-means-cluster (k=3) the current cross-factor performance
   scores into {worst, average, best}; pick the factor whose score is
   closest to the CHOSEN cluster's centroid (from_cluster param, default
   "best" per source's default recommendation) and use that factor's
   SuperTrend line/direction as the live signal for this bar.
4. Position = 1 (long) when the selected factor's SuperTrend direction is
   bullish (trailing stop below price); 0 (flat) otherwise. Long-only,
   consistent with this repo's other trend-following strategies.

Because true k-means with random initialization would be non-causal/
non-deterministic across runs, this implementation uses a small closed-form
1-D k-means (quantile-seeded, few Lloyd iterations) run bar-by-bar only on
information available up to that bar (causal).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept the strategy's parameters as keyword arguments (grid-test
contract).
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


def _atr(df: pd.DataFrame, length: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(length).mean()


def _supertrend_line(df: pd.DataFrame, atr: pd.Series, factor: float) -> pd.Series:
    """Classic SuperTrend direction series: +1 bullish, -1 bearish."""
    close = df["close"]
    hl2 = (df["high"] + df["low"]) / 2.0
    upper_basic = hl2 + factor * atr
    lower_basic = hl2 - factor * atr

    n = len(close)
    final_upper = np.full(n, np.nan)
    final_lower = np.full(n, np.nan)
    direction = np.ones(n)

    close_v = close.values
    upper_v = upper_basic.values
    lower_v = lower_basic.values

    for i in range(n):
        if i == 0 or np.isnan(atr.iloc[i]):
            final_upper[i] = upper_v[i]
            final_lower[i] = lower_v[i]
            direction[i] = 1
            continue
        # Final upper band
        if upper_v[i] < final_upper[i - 1] or close_v[i - 1] > final_upper[i - 1]:
            final_upper[i] = upper_v[i]
        else:
            final_upper[i] = final_upper[i - 1]
        # Final lower band
        if lower_v[i] > final_lower[i - 1] or close_v[i - 1] < final_lower[i - 1]:
            final_lower[i] = lower_v[i]
        else:
            final_lower[i] = final_lower[i - 1]
        # Direction
        prev_dir = direction[i - 1]
        if prev_dir == 1:
            direction[i] = -1 if close_v[i] < final_lower[i] else 1
        else:
            direction[i] = 1 if close_v[i] > final_upper[i] else -1

    return pd.Series(direction, index=close.index)


def _kmeans_1d(values: np.ndarray, k: int = 3, iters: int = 10) -> np.ndarray:
    """Tiny deterministic 1-D k-means. Returns cluster label per value."""
    if len(values) < k:
        return np.zeros(len(values), dtype=int)
    # Quantile-seeded centroids (deterministic, causal -- no randomness).
    qs = np.linspace(0.15, 0.85, k)
    centroids = np.quantile(values, qs)
    labels = np.zeros(len(values), dtype=int)
    for _ in range(iters):
        dists = np.abs(values[:, None] - centroids[None, :])
        labels = np.argmin(dists, axis=1)
        for c in range(k):
            mask = labels == c
            if mask.any():
                centroids[c] = values[mask].mean()
    # Sort cluster ids by centroid value ascending so label 0=worst, k-1=best
    order = np.argsort(centroids)
    remap = {old: new for new, old in enumerate(order)}
    return np.array([remap[l] for l in labels])


def generate_signals(
    price_df: pd.DataFrame,
    atr_length: int = 10,
    factor_min: float = 1.0,
    factor_max: float = 5.0,
    factor_step: float = 1.0,
    performance_memory: float = 10.0,
    from_cluster: str = "best",
    recompute_every: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    atr = _atr(df, atr_length)

    factors = np.arange(factor_min, factor_max + 1e-9, factor_step)
    directions = {f: _supertrend_line(df, atr, f) for f in factors}

    n = len(close)
    ret_sign = np.sign(close.pct_change().fillna(0.0).values)
    decay = 1.0 - (1.0 / max(performance_memory, 1.0))

    perf = {f: np.zeros(n) for f in factors}
    dir_arrays = {f: directions[f].values for f in factors}
    for f in factors:
        d = dir_arrays[f]
        p = perf[f]
        running = 0.0
        for i in range(1, n):
            agree = ret_sign[i] * d[i - 1]
            running = running * decay + agree
            p[i] = running

    cluster_target = {"worst": 0, "average": 1, "best": 2}
    target_label = cluster_target.get(from_cluster, 2)

    selected_dir = np.zeros(n)
    warmup = max(atr_length, int(performance_memory) + 1)
    last_choice_idx = 0
    chosen_factor_series = None
    for i in range(n):
        if i < warmup:
            selected_dir[i] = 1
            continue
        if (i - warmup) % max(recompute_every, 1) == 0 or chosen_factor_series is None:
            scores = np.array([perf[f][i] for f in factors])
            labels = _kmeans_1d(scores, k=min(3, len(factors)))
            target = min(target_label, labels.max())
            candidates = np.where(labels == target)[0]
            if len(candidates) == 0:
                candidates = np.arange(len(factors))
            best_idx = candidates[np.argmax(scores[candidates])]
            chosen_factor_series = factors[best_idx]
        selected_dir[i] = dir_arrays[chosen_factor_series][i]

    position = (pd.Series(selected_dir, index=close.index) > 0).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

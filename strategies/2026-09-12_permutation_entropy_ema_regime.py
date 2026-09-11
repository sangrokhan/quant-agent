"""Strategy: Permutation-Entropy regime-gated EMA crossover trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Permutation Entropy (PE, Bandt & Pompe 2002) measures the "order" vs
"chaos" of a price series by computing the Shannon entropy of the relative
ordinal-rank patterns ("motifs") of overlapping windows of length
`embed_dim`, rather than raw price values -- making it robust to noise and
sensitive purely to the *sequence structure* of ups/downs. Per
https://kr.tradingview.com/script/wPxhw6y6-Permutation-Entropy-Complexity-Oscillator/
(GospodarValovaHR, via browser_exec/google.com fallback -- web_search DDGS
backend failed with TLS/connection errors on this iteration's queries):
"Low Entropy (Green Zone): The market is structured and predictable...
indicates a strong trending regime... Confirm the Trend: When the line is
Green (Predictable), the market has high structural order. This is the
time to look for entries using your favorite trend-following system...
Avoid the Chop: When the line is Red (High Chaos), avoid trend-following
entries." Operationalized as: compute rolling permutation entropy (embed_dim
patterns, normalized to [0,1] by log(embed_dim!)) over `pe_window` bars;
gate a standard fast/slow EMA crossover trend-following signal so entries
only fire when PE <= a low-entropy threshold (structured/trending regime),
flat (or exit) when PE rises above threshold (chaotic/choppy regime) or on
the bearish EMA cross.

Distinct from the already-tested Approximate-Entropy (ApEn) breakout gate
(2026-09-08-047, which gates an SMA-trend BREAKOUT using amplitude-tolerance
entropy on RETURNS) and Hurst-exponent regime filters (2026-09-04-155/156,
R/S analysis persistence measure) -- Permutation Entropy is a distinct
ordinal-pattern/rank-based information-theoretic measure, and this strategy
gates an EMA CROSSOVER (not a breakout or mean-reversion z-score) signal.
First Permutation Entropy strategy in this repo.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import math
from itertools import permutations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ordinal_pattern(window: np.ndarray) -> tuple:
    """Return the ordinal (rank) pattern of a small window, e.g. (0,2,1)."""
    return tuple(np.argsort(window))


def _rolling_permutation_entropy(close: pd.Series, embed_dim: int, pe_window: int) -> pd.Series:
    """Rolling normalized permutation entropy (0..1), Bandt & Pompe (2002).

    Vectorized: first compute every bar's ordinal-pattern CODE (an integer
    0..embed_dim!-1 identifying its rank pattern) via a sliding-window view,
    then roll a histogram of those codes over `pe_window` bars and compute
    Shannon entropy per window -- avoids a Python-level double loop over
    both bars and sub-windows, which is the previous implementation's
    O(n * pe_window) bottleneck.

    0 = perfectly ordered/repeating pattern, 1 = maximal disorder/chaos.
    """
    vals = close.values.astype(float)
    n = len(vals)
    all_patterns = list(permutations(range(embed_dim)))
    pattern_index = {p: i for i, p in enumerate(all_patterns)}
    n_patterns = len(all_patterns)
    max_entropy = math.log(n_patterns)

    if n < embed_dim:
        return pd.Series(np.nan, index=close.index)

    # sliding_window_view: shape (n-embed_dim+1, embed_dim)
    windows = np.lib.stride_tricks.sliding_window_view(vals, embed_dim)
    ranks = np.argsort(windows, axis=1)
    codes = np.empty(len(ranks), dtype=np.int64)
    for i, r in enumerate(map(tuple, ranks)):
        codes[i] = pattern_index[r]
    # codes[i] corresponds to bar index i+embed_dim-1 in the original series

    codes_series = pd.Series(codes)
    # one-hot columns per pattern code, rolling-summed over pe_window
    onehot = pd.get_dummies(codes_series)
    # ensure all pattern columns present
    for c in range(n_patterns):
        if c not in onehot.columns:
            onehot[c] = 0
    onehot = onehot[sorted(onehot.columns)]
    counts = onehot.rolling(pe_window, min_periods=pe_window).sum()

    totals = counts.sum(axis=1)
    probs = counts.div(totals.replace(0, np.nan), axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        logp = np.log(probs.where(probs > 0))
    entropy = -(probs.where(probs > 0) * logp).sum(axis=1)
    pe_codes_index = entropy / max_entropy if max_entropy > 0 else entropy * np.nan

    pe = pd.Series(np.nan, index=close.index)
    pe.iloc[embed_dim - 1 :] = pe_codes_index.values
    return pe


def generate_signals(
    price_df: pd.DataFrame,
    embed_dim: int = 3,
    pe_window: int = 60,
    pe_threshold: float = 0.85,
    fast_ema: int = 20,
    slow_ema: int = 50,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    pe = _rolling_permutation_entropy(close, embed_dim, pe_window)
    low_entropy_regime = pe <= pe_threshold

    ema_fast = close.ewm(span=fast_ema, adjust=False).mean()
    ema_slow = close.ewm(span=slow_ema, adjust=False).mean()
    bullish_cross = ema_fast > ema_slow
    prev_bullish = bullish_cross.shift(1)
    cross_up = bullish_cross & ~prev_bullish.fillna(False)
    cross_down = ~bullish_cross & prev_bullish.fillna(False)

    entry = cross_up.fillna(False) & low_entropy_regime.fillna(False)
    exit_cross = cross_down.fillna(False)
    exit_regime_flip = ~low_entropy_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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

"""Strategy: Vortex Indicator crossover entry, SEPARATION-CONVERGENCE exit.

Hypothesis (source: https://www.quantum-algo.com/blog/guides/vortex-indicator-complete-guide/,
read via browser_exec fallback after web_extract's DDGS backend could not
extract page content -- see knowledge_base/visited_pages.jsonl):

The source's own key emphasis, distinct from the plain VI+/VI- crossover
already tested repeatedly in this repo (2026-09-04-040 accepted QQQ-only,
2026-09-06-091 ADX-gated variant, 2026-09-13 diff-ratio sizing variant,
2026-09-16 TSI dual-confirmation variant), is that "as [VI+/VI-] converge,
the trend is losing steam, often well before the cross confirms a reversal.
Reading separation gives you an early read on trend health that the cross
alone cannot provide." This strategy tests that specific, distinct exit
mechanic: enter long on a standard VI+ crossing above VI- (bullish cross),
but EXIT not on the opposing crossover (the mechanic every prior Vortex
entry in this repo has used) but instead when the separation |VI+ - VI-|
collapses back below a convergence threshold (lines "braiding" = trend
losing conviction), which the source claims happens earlier than a full
reversal cross. A max_hold_days time-stop backstops indefinite holds.

Signal logic
------------
- VI+ / VI- computed over `vi_period` bars (standard formula: VM+ = |high -
  prior low|, VM- = |low - prior high|, summed over vi_period and
  normalized by summed true range over the same window).
- Entry (long): VI+ crosses above VI- (bullish cross), AND separation at
  entry (VI+ - VI-) is at least `min_entry_separation` (source's own
  "scissors opening" strong-trend confirmation, filtering out weak/noisy
  crosses near the 1.0 braid zone).
- Exit: separation (VI+ - VI-) drops below `exit_convergence_threshold`
  (lines re-converging -- the source's claimed early-warning signal,
  distinct from waiting for a full opposite cross), OR VI- crosses back
  above VI+ (safety net if convergence exit is somehow skipped), OR
  `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _vortex(df: pd.DataFrame, vi_period: int) -> tuple[pd.Series, pd.Series]:
    high, low, close = df["high"], df["low"], df["close"]
    prior_low = low.shift(1)
    prior_high = high.shift(1)
    prior_close = close.shift(1)

    vm_plus = (high - prior_low).abs()
    vm_minus = (low - prior_high).abs()

    tr = pd.concat([
        (high - low).abs(),
        (high - prior_close).abs(),
        (low - prior_close).abs(),
    ], axis=1).max(axis=1)

    sum_vm_plus = vm_plus.rolling(vi_period).sum()
    sum_vm_minus = vm_minus.rolling(vi_period).sum()
    sum_tr = tr.rolling(vi_period).sum().replace(0, pd.NA)

    vi_plus = sum_vm_plus / sum_tr
    vi_minus = sum_vm_minus / sum_tr
    return vi_plus.astype(float), vi_minus.astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    vi_period: int = 14,
    min_entry_separation: float = 0.10,
    exit_convergence_threshold: float = 0.03,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    vi_plus, vi_minus = _vortex(df, vi_period)
    sep = vi_plus - vi_minus

    bullish_cross = (vi_plus > vi_minus) & (vi_plus.shift(1) <= vi_minus.shift(1))
    strong_entry = bullish_cross & (sep >= min_entry_separation)
    convergence_exit = sep.abs() < exit_convergence_threshold
    reversal_exit = (vi_minus > vi_plus) & (vi_minus.shift(1) <= vi_plus.shift(1))

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    strong_entry_vals = strong_entry.fillna(False).to_numpy()
    convergence_exit_vals = convergence_exit.fillna(False).to_numpy()
    reversal_exit_vals = reversal_exit.fillna(False).to_numpy()

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if convergence_exit_vals[i] or reversal_exit_vals[i] or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if strong_entry_vals[i]:
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

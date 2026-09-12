"""Strategy: Apirine True Range Adjusted EMA (TRAdj EMA) dual-length crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-196):
Per Vitali Apirine's S&C January 2023 "True Range Adjusted Exponential
Moving Average" article (TASC Traders' Tips 2023.01, fully disclosed
formula via TradingView PineCodersTASC implementation notes):

  TR = standard Wilder True Range.
  TRAdj = (Current TR - Minimum TR) / (Maximum TR - Minimum TR), where
          Minimum/Maximum TR are over a `tr_lookback`-bar window.
  TRAdj EMA weighting factor = 2*(1 + TRAdj*Multiplier) / (ema_length + 1)
          (vs. a traditional EMA's fixed 2/(ema_length+1)), where
          Multiplier ranges 5-10 per source.

This makes the EMA's effective smoothing speed up (more weight on the
current bar) exactly when the CURRENT bar's true range is near the top of
its recent range (volatility expansion), and slow down when TR is near
its recent low (volatility contraction) -- a volatility-adaptive EMA
distinct from Kaufman's Efficiency-Ratio-based KAMA (already tested,
2026-09-04_efficiency_ratio_wma_trend.py /
2026-09-04_kama_crossover_slope.py) which adapts to TREND EFFICIENCY, not
raw volatility expansion/contraction.

Source's own suggested usage ("use a TRAdj EMA alongside another TRAdj EMA
of a different length to identify turning points"): this strategy
implements a DUAL-LENGTH TRAdj EMA crossover -- long when the fast TRAdj
EMA crosses above the slow TRAdj EMA, flat on the mirror bearish cross.
First TRAdj-EMA-family strategy in this repo.

Signal logic
------------
- Compute TR, TRAdj (using `tr_lookback`), and the TRAdj-EMA recursively
  for two lengths: `fast_length` and `slow_length` (both share the same
  Multiplier).
- Long entry: fast TRAdj EMA crosses above slow TRAdj EMA.
- Exit (flatten): fast TRAdj EMA crosses below slow TRAdj EMA.

Interface contract for validators (see validation/validators.py) and
grid_test (see validation/grid_test.py):
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).

Tunable params (all keyword args, per RESEARCH_LOOP.md Step 5 contract):
    fast_length  (fast TRAdj EMA length, default 10).
    slow_length  (slow TRAdj EMA length, default 30).
    tr_lookback  (TR min/max lookback window, default 20).
    multiplier   (source's own Multiplier input, range 5-10 per article,
        default 7.5, midpoint of source's suggested range).
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


def _true_range(df: pd.DataFrame) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _tradj_ema(close: pd.Series, tr: pd.Series, tr_lookback: int, ema_length: int, multiplier: float) -> pd.Series:
    min_tr = tr.rolling(tr_lookback, min_periods=tr_lookback).min()
    max_tr = tr.rolling(tr_lookback, min_periods=tr_lookback).max()
    tr_range = (max_tr - min_tr).replace(0.0, np.nan)
    tradj = ((tr - min_tr) / tr_range).fillna(0.0).clip(0.0, 1.0)

    vals = close.to_numpy(dtype=float)
    tradj_vals = tradj.to_numpy(dtype=float)
    m = len(vals)
    out = np.full(m, np.nan)

    first_valid = tr_lookback  # once TR window is full
    if first_valid >= m:
        return pd.Series(out, index=close.index)

    out[first_valid] = vals[first_valid]
    for t in range(first_valid + 1, m):
        alpha = 2.0 * (1.0 + tradj_vals[t] * multiplier) / (ema_length + 1.0)
        alpha = min(alpha, 1.0)
        out[t] = alpha * vals[t] + (1.0 - alpha) * out[t - 1]

    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    fast_length: int = 10,
    slow_length: int = 30,
    tr_lookback: int = 20,
    multiplier: float = 7.5,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    tr = _true_range(df)
    fast_ema = _tradj_ema(close, tr, tr_lookback, fast_length, multiplier)
    slow_ema = _tradj_ema(close, tr, tr_lookback, slow_length, multiplier)

    bullish = fast_ema > slow_ema

    position = pd.Series(0, index=close.index, dtype=int)
    pos = 0
    for i in range(len(close)):
        if np.isnan(fast_ema.iloc[i]) or np.isnan(slow_ema.iloc[i]):
            position.iloc[i] = 0
            continue
        pos = 1 if bullish.iloc[i] else 0
        position.iloc[i] = pos

    return position


def generate_returns(
    price_df: pd.DataFrame,
    fast_length: int = 10,
    slow_length: int = 30,
    tr_lookback: int = 20,
    multiplier: float = 7.5,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        fast_length=fast_length,
        slow_length=slow_length,
        tr_lookback=tr_lookback,
        multiplier=multiplier,
    )
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

"""Strategy: Apirine TRAdj EMA dual-length crossover with min-hold hysteresis
filter (direct fix for rejected high-turnover 2026-09-12-196).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-197):
Direct fix attempt for 2026-09-12-196 (Apirine TRAdj EMA dual-length
crossover, rejected: both QQQ and SPY failed Sharpe AND MDD on the full
sample, with very high turnover -- 162-165 trades over ~8.5 years, ~19-20
trades/year). That report's own noted future direction: "add min-hold
hysteresis filter to reduce whipsaw (established fix pattern in this repo
for high-turnover near-misses)" -- referencing this repo's repeated
successful use of the same fix (e.g. Klinger 2026-09-04-085, ZLEMA
2026-09-06-171, Accelerator Oscillator 2026-09-06-174, Correlation Cycle
2026-09-12-139).

This iteration adds a `min_hold_days` parameter: once a position is
entered/exited, the opposite signal is ignored until at least
`min_hold_days` bars have elapsed, suppressing the rapid TRAdj-EMA
crossovers responsible for the excessive trade count and (per source's
own construction) the whipsaw around volatility-driven weighting-factor
noise.

Signal logic
------------
- Same dual TRAdj-EMA crossover construction as 2026-09-12-196 (fast vs
  slow TRAdj EMA, both sharing tr_lookback/multiplier).
- Raw crossover signal: bullish = fast TRAdj EMA > slow TRAdj EMA.
- Position only flips when the raw signal has been consistently opposite
  the current position for at least `min_hold_days` consecutive bars
  (hysteresis), rather than flipping on every single-bar crossover.

Interface contract for validators (see validation/validators.py) and
grid_test (see validation/grid_test.py):
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).

Tunable params (all keyword args, per RESEARCH_LOOP.md Step 5 contract):
    fast_length   (fast TRAdj EMA length, default 8, prior iteration's
        best config).
    slow_length   (slow TRAdj EMA length, default 40, prior iteration's
        best config).
    tr_lookback   (TR min/max lookback window, default 20).
    multiplier    (source's own Multiplier input, default 7.5).
    min_hold_days (NEW hysteresis filter: minimum consecutive bars the raw
        signal must persist opposite the current position before
        flipping, default 5).
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

    first_valid = tr_lookback
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
    fast_length: int = 8,
    slow_length: int = 40,
    tr_lookback: int = 20,
    multiplier: float = 7.5,
    min_hold_days: int = 5,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    tr = _true_range(df)
    fast_ema = _tradj_ema(close, tr, tr_lookback, fast_length, multiplier)
    slow_ema = _tradj_ema(close, tr, tr_lookback, slow_length, multiplier)

    raw_bullish = (fast_ema > slow_ema).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    pos = 0
    opposite_streak = 0
    for i in range(len(close)):
        if np.isnan(fast_ema.iloc[i]) or np.isnan(slow_ema.iloc[i]):
            position.iloc[i] = 0
            continue

        desired = 1 if raw_bullish.iloc[i] else 0
        if desired != pos:
            opposite_streak += 1
            if opposite_streak >= min_hold_days:
                pos = desired
                opposite_streak = 0
        else:
            opposite_streak = 0

        position.iloc[i] = pos

    return position


def generate_returns(
    price_df: pd.DataFrame,
    fast_length: int = 8,
    slow_length: int = 40,
    tr_lookback: int = 20,
    multiplier: float = 7.5,
    min_hold_days: int = 5,
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
        min_hold_days=min_hold_days,
    )
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

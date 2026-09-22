"""Strategy: CMMA (Close Minus Moving Average, ATR-normalized) mean
reversion.

Source: Aligrithm "2.12 CMMA: A Better Momentum Primitive Than
Price-minus-MA Alone" (4 May 2026),
https://aligrithm.com/cmma-a-better-momentum-primitive-than-price-minus-ma-alone/
(visited 2026-09-23, see knowledge_base/visited_pages.jsonl).

Source's fully disclosed formula (an engineered momentum/mean-reversion
PRIMITIVE, framed for ML feature use, not itself a strategy with disclosed
thresholds -- the threshold-based long/flat rule below is this repo's own
adaptation of the primitive, following the standard oscillator-threshold
pattern already used throughout this repo, e.g. CMO/z-score/disparity-index
mean-reversion strategies):

    CMMA(k)_t = [ln(C_t) - mean_{i=1..k}(ln(C_{t-i}))] / [ATR_W(ln C)_t * sqrt(k+1)]

Four structural ingredients, each fixing a specific failure of the plain
Close-minus-MA construction (source's own stated rationale):
  1. Log prices, not raw prices (proportional return, cross-instrument/
     cross-time comparable scale).
  2. The MA is computed over bars t-1..t-k ONLY (excludes bar t) -- avoids
     self-attenuation of the signal (k/(k+1) shrink factor) and avoids
     look-ahead.
  3. ATR (computed on LOG prices, window W) INCLUDES the current bar t --
     puts numerator (today's regime) and denominator (today's regime) on
     the same footing; source explicitly argues this is not a look-ahead
     since ATR is a scaling factor, not the predictive numerator.
  4. sqrt(k+1) divisor -- makes CMMA lookback-length-independent under an
     i.i.d.-random-walk null (numerator stdev scales as sqrt(k+1) under
     that null).

Source's stated defaults: W=100 for k up to 30, W=250 for k up to 100.

This repo's mean-reversion adaptation: go long when CMMA crosses below a
negative entry threshold (price is statistically far below its own recent
log-price trend, in ATR-normalized units); exit/flat when CMMA reverts back
above an exit threshold (default 0, full mean reversion) or a max_hold_days
time-stop safety backstop, following the same threshold-oscillator pattern
as this repo's existing CMO/disparity-index/z-score mean-reversion
strategies (first CMMA-family entry in this repo).

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _atr_log(df: pd.DataFrame, window: int) -> pd.Series:
    """ATR computed on log(high), log(low), log(close) -- true range on the
    log-price scale, matching the source's "ATR_W(ln C)" notation (ATR of
    the log-price series, current bar included)."""
    log_high = np.log(df["high"])
    log_low = np.log(df["low"])
    log_close = np.log(df["close"])
    prev_log_close = log_close.shift(1)

    tr = pd.concat(
        [
            log_high - log_low,
            (log_high - prev_log_close).abs(),
            (log_low - prev_log_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    # Wilder-style rolling mean, current bar included (per source).
    atr = tr.rolling(window, min_periods=window).mean()
    return atr


def _cmma(df: pd.DataFrame, k: int, atr_window: int) -> pd.Series:
    log_close = np.log(df["close"])
    # MA over PREVIOUS k bars only (excludes bar t).
    ma_prev = log_close.shift(1).rolling(k, min_periods=k).mean()
    numerator = log_close - ma_prev
    atr = _atr_log(df, atr_window)
    denom = atr * np.sqrt(k + 1)
    cmma = numerator / denom.replace(0.0, np.nan)
    return cmma


def _simulate(
    price_df: pd.DataFrame,
    k: int = 20,
    atr_window: int = 100,
    entry_threshold: float = -1.5,
    exit_threshold: float = 0.0,
    max_hold_days: int = 20,
) -> pd.DataFrame:
    df = _prep(price_df)
    cmma = _cmma(df, k, atr_window)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = -1
    idx_list = df.index

    cmma_vals = cmma.values
    n = len(df)
    pos_arr = np.zeros(n, dtype=int)

    for i in range(n):
        val = cmma_vals[i]
        if not in_position:
            if not np.isnan(val) and val <= entry_threshold:
                in_position = True
                entry_idx = i
        else:
            held_days = i - entry_idx
            reverted = (not np.isnan(val)) and (val >= exit_threshold)
            timed_out = held_days >= max_hold_days
            if reverted or timed_out:
                in_position = False
        pos_arr[i] = 1 if in_position else 0

    position = pd.Series(pos_arr, index=idx_list)
    # Apply yesterday's decided position to today's return (avoid look-ahead).
    position_applied = position.shift(1).fillna(0).astype(int)
    strat_ret = daily_ret * position_applied

    return pd.DataFrame({"position": position_applied, "returns": strat_ret}, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    k: int = 20,
    atr_window: int = 100,
    entry_threshold: float = -1.5,
    exit_threshold: float = 0.0,
    max_hold_days: int = 20,
) -> pd.Series:
    result = _simulate(price_df, k, atr_window, entry_threshold, exit_threshold, max_hold_days)
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    k: int = 20,
    atr_window: int = 100,
    entry_threshold: float = -1.5,
    exit_threshold: float = 0.0,
    max_hold_days: int = 20,
) -> pd.Series:
    result = _simulate(price_df, k, atr_window, entry_threshold, exit_threshold, max_hold_days)
    return result["returns"]

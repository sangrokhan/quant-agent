"""Strategy: TradingView Chop Zone Indicator directional entry, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: Google AI Overview (accessed 2026-09-22, corroborated by
LuxAlgo/Angel One/FX Replay Chop Zone Indicator explainers). The Chop Zone
indicator maps the Choppiness Index (Bill Dreiss's formula, log10(sum(TR,
n)/(max(high,n)-min(low,n)))/log10(n)*100) to specific color-coded
directional zones using the SAME Fibonacci-derived boundaries (38.2, 45,
55, 61.8) already tested in this repo's Choppiness-Index-as-trend-gate
entry (2026-09-09-008, rejected for insufficient sample: only 3 trades),
but Chop Zone's construction and TRADING RULE are meaningfully different:
  1. Chop Zone additionally checks the DIRECTION of a linear-regression-like
     slope on the EMA basis (rising vs falling), not just the raw CHOP
     value magnitude -- distinguishing "trending up" (dark blue, CHOP>61.8
     AND EMA rising) from "trending down" (dark purple, CHOP<38.2 AND EMA
     falling), rather than 2026-09-09-008's single CHOP<45 gate applied to
     an EMA crossover.
  2. The disclosed trading rule requires price ABOVE a 34-period EMA
     baseline (not the EMA crossover trigger itself) as confirmation,
     entering AFTER the zone has printed consecutively for
     `confirm_bars` bars (avoiding single-bar noise), and exiting flat as
     soon as the zone reverts to "chop" (Yellow/Black, i.e. CHOP in
     [38.2, 61.8]) rather than exiting on an EMA cross.
This iteration deliberately reuses the repo's own already-implemented
Choppiness Index math (from 2026-09-09-008's rejected attempt, per the
KB's "no re-fetch, note-based dedupe" convention for formulas already
documented) but wraps it in the Chop Zone's distinct color-zone + EMA-slope
+ consecutive-bar-confirmation trading logic, which was never tested here.

Signal logic (daily bars, causal/no look-ahead)
------------------------------------------------
- True Range and Choppiness Index (CHOP) over `chop_window` bars:
  CHOP = 100 * log10(sum(TR, chop_window) / (HH - LL)) / log10(chop_window)
- EMA(ema_window) baseline (default 34, per source).
- "Trending up" zone: CHOP > upper_thresh (61.8) AND EMA is rising
  (EMA[t] > EMA[t-1]).
- Entry (long): trending-up zone holds for `confirm_bars` consecutive bars
  AND close > EMA(ema_window).
- Exit: CHOP falls back into the chop band (lower_thresh <= CHOP <=
  upper_thresh, i.e. no longer "strongly trending up") OR close < EMA
  baseline, whichever comes first.
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
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    return pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def _choppiness(df: pd.DataFrame, window: int) -> pd.Series:
    tr = _true_range(df)
    sum_tr = tr.rolling(window).sum()
    hh = df["high"].rolling(window).max()
    ll = df["low"].rolling(window).min()
    rng = (hh - ll).replace(0, np.nan)
    chop = 100 * np.log10(sum_tr / rng) / np.log10(window)
    return chop


def generate_signals(
    price_df: pd.DataFrame,
    chop_window: int = 14,
    ema_window: int = 34,
    upper_thresh: float = 61.8,
    lower_thresh: float = 38.2,
    confirm_bars: int = 2,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    chop = _choppiness(df, chop_window)
    ema = close.ewm(span=ema_window, adjust=False).mean()
    ema_rising = ema > ema.shift(1)

    trending_up = (chop > upper_thresh) & ema_rising
    trending_up_run = trending_up.rolling(confirm_bars).sum() >= confirm_bars

    entry = trending_up_run & (close > ema)
    exit_signal = ((chop >= lower_thresh) & (chop <= upper_thresh)) | (close < ema)

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_arr = entry.fillna(False).to_numpy()
    exit_arr = exit_signal.fillna(True).to_numpy()

    for i in range(len(close)):
        if not in_pos:
            if entry_arr[i]:
                in_pos = True
                position.iloc[i] = 1
        else:
            if exit_arr[i]:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    chop_window: int = 14,
    ema_window: int = 34,
    upper_thresh: float = 61.8,
    lower_thresh: float = 38.2,
    confirm_bars: int = 2,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        chop_window=chop_window,
        ema_window=ema_window,
        upper_thresh=upper_thresh,
        lower_thresh=lower_thresh,
        confirm_bars=confirm_bars,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

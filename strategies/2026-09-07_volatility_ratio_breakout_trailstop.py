"""Strategy: Volatility Ratio (TR/ATR) single-bar range-expansion breakout,
long-only, adapted from a long/short futures template.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-019):
Per https://pinescriptforge.com/strategy/volatility-ratio-breakout: the
Volatility Ratio (VR) = today's True Range / ATR(atr_window) is a
normalized single-bar range-expansion metric. When VR exceeds a threshold
(source default 2.0), that bar is a "breakout bar that often initiates a
new trend leg". Source's entry logic: trade in the direction of the
breakout bar (bullish if close > open, bearish if close < open) -- adapted
here to LONG-ONLY (bullish breakout bars only) per this repo's SAFETY.md
(source's original strategy is long/short-symmetric on futures). Exit:
trail a stop at `trail_atr_mult` x ATR (source: 1.5x ATR), or take profit
when VR normalizes below `normalize_threshold` (source: 1.0) for
`normalize_bars` consecutive bars (source: 3).

Distinct from this repo's existing volatility-expansion strategies:
- 2026-09-05-055 (ATR-expansion + EMA band breakout + SMA trend filter):
  gates entry on ATR itself vs. its OWN rolling average, plus an EMA-band
  breakout and SMA trend filter -- three conditions.
- 2026-09-06-109 (HVR, ratio of two different-horizon realized-vol std-devs
  of log returns): a smoother multi-bar ratio, no trend/breakout condition.
This strategy uses a single-bar True-Range-to-ATR ratio (no smoothing on
the numerator) with a same-bar directional trigger and a trailing-ATR-stop
exit mechanism, none of which the prior two share.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def _atr(df: pd.DataFrame, window: int) -> tuple[pd.Series, pd.Series]:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(window).mean()
    return tr, atr


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    vr_threshold: float = 2.0,
    trail_atr_mult: float = 1.5,
    normalize_threshold: float = 1.0,
    normalize_bars: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    tr, atr = _atr(df, atr_window)
    vr = (tr / atr.replace(0, np.nan)).fillna(0.0)

    bullish_breakout = (vr > vr_threshold) & (close > open_)
    vr_below_norm = vr < normalize_threshold
    # count of consecutive bars with VR below the normalize threshold
    norm_run = (
        vr_below_norm.groupby((~vr_below_norm).cumsum()).cumcount() + 1
    ) * vr_below_norm

    n = len(close)
    close_vals = close.values
    atr_vals = atr.values
    bullish_vals = bullish_breakout.values
    norm_run_vals = norm_run.values

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    trail_stop = -np.inf

    for i in range(n):
        if not in_pos:
            if bullish_vals[i]:
                in_pos = True
                trail_stop = close_vals[i] - trail_atr_mult * (
                    atr_vals[i] if not np.isnan(atr_vals[i]) else 0.0
                )
            position.iloc[i] = 1 if in_pos else 0
            continue

        # update trailing stop upward only (long-only trailing stop)
        candidate_stop = close_vals[i] - trail_atr_mult * (
            atr_vals[i] if not np.isnan(atr_vals[i]) else 0.0
        )
        trail_stop = max(trail_stop, candidate_stop)

        hit_stop = close_vals[i] <= trail_stop
        take_profit = norm_run_vals[i] >= normalize_bars

        if hit_stop or take_profit:
            in_pos = False
            position.iloc[i] = 0
            trail_stop = -np.inf
        else:
            position.iloc[i] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

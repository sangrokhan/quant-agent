"""Strategy: Donchian-channel breakout, gated by a Shannon-entropy trend/chop regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Per Richard Shu's "Trading with Less Surprise: Using Shannon Entropy to
Improve a Breakout Strategy" (Medium/CodeX, Nov 2025,
https://medium.com/codex/trading-with-less-surprise-using-shannon-entropy-to-improve-a-breakout-strategy-4d0a15098cba,
read via browser_exec this iteration -- web_search DDGS backend intermittently
failing, browser fallback used), classic Donchian-channel breakouts suffer
from "false breakouts" in choppy/high-entropy markets, where price pierces
the channel and immediately reverses. Shannon entropy of the rolling
short-window return distribution (discretized into bins) measures how
"random"/unstructured recent price action has been; a NEGATIVE rolling
z-score of that entropy (current entropy below its own trailing-year
average) indicates a more structured/trending regime, in which breakouts
are more likely to persist rather than fail. The source's own walk-forward
backtest (SPY, 2000-2025, entropy_lookback=20, threshold_window=252) found
gating/features a Donchian breakout ML model with entropy_zscore improved
Sharpe from 0.351 to 0.455 (+29.6%) and Max Drawdown from -12.57% to -9.68%.

This repo adapts the *feature* into a hard binary regime GATE (rather than
an ML model input, since this repo's strategies are rule-based, not
ML-driven): only take Donchian breakout entries when entropy_zscore <=
entropy_gate_threshold (i.e. we are in a low-entropy/trending regime).
First Shannon-entropy-based strategy in this repo (distinct from the
existing permutation-entropy / approximate-entropy / fractal-dimension
entries, which used different entropy estimators and different base
signals).

Signal logic
------------
- Rolling Shannon entropy of daily log returns over `entropy_lookback` days
  (returns discretized into `entropy_bins` equal-width bins via pd.cut,
  entropy = -sum(p*log2(p))).
- entropy_zscore = (entropy - rolling_mean(entropy, threshold_window)) /
  rolling_std(entropy, threshold_window).
- Donchian channel: upper = rolling max(high, donchian_window) shifted by 1
  (so today's breakout compares against the PRIOR window, no lookahead);
  lower = rolling min(low, donchian_window) shifted by 1.
- Entry (long): close > upper (breakout) AND entropy_zscore <=
  entropy_gate_threshold (low-entropy/trending regime confirmed).
- Exit: close < lower_exit (rolling min(low, donchian_exit_window), a
  looser trailing channel used as an exit stop) OR after max_hold_days.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept params as keyword arguments per Step 5 of RESEARCH_LOOP.md.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _shannon_entropy(window: np.ndarray, bins: int) -> float:
    arr = window[~np.isnan(window)]
    if len(arr) < 2:
        return np.nan
    try:
        counts, _ = np.histogram(arr, bins=bins)
    except Exception:
        return np.nan
    total = counts.sum()
    if total == 0:
        return np.nan
    probs = counts[counts > 0] / total
    return float(-np.sum(probs * np.log2(probs)))


def _compute_entropy_zscore(
    close: pd.Series,
    entropy_lookback: int,
    entropy_bins: int,
    threshold_window: int,
) -> pd.Series:
    log_ret = np.log(close / close.shift(1))
    entropy = log_ret.rolling(entropy_lookback).apply(
        lambda w: _shannon_entropy(w.values, entropy_bins), raw=False
    )
    entropy_mean = entropy.rolling(threshold_window, min_periods=entropy_lookback).mean()
    entropy_std = entropy.rolling(threshold_window, min_periods=entropy_lookback).std()
    zscore = (entropy - entropy_mean) / entropy_std.replace(0.0, np.nan)
    return zscore.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    donchian_window: int = 20,
    donchian_exit_window: int = 10,
    entropy_lookback: int = 20,
    entropy_bins: int = 10,
    threshold_window: int = 252,
    entropy_gate_threshold: float = 0.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    upper = high.rolling(donchian_window).max().shift(1)
    lower_exit = low.rolling(donchian_exit_window).min().shift(1)

    entropy_zscore = _compute_entropy_zscore(
        close, entropy_lookback, entropy_bins, threshold_window
    )
    low_entropy_regime = entropy_zscore <= entropy_gate_threshold

    breakout = close > upper
    entry_signal = breakout & low_entropy_regime

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_days = 0
    for i in range(len(close)):
        if in_pos:
            hold_days += 1
            exit_now = (close.iloc[i] < lower_exit.iloc[i]) or (hold_days >= max_hold_days)
            if exit_now:
                in_pos = False
                hold_days = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_pos = True
                hold_days = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    donchian_window: int = 20,
    donchian_exit_window: int = 10,
    entropy_lookback: int = 20,
    entropy_bins: int = 10,
    threshold_window: int = 252,
    entropy_gate_threshold: float = 0.0,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        donchian_window=donchian_window,
        donchian_exit_window=donchian_exit_window,
        entropy_lookback=entropy_lookback,
        entropy_bins=entropy_bins,
        threshold_window=threshold_window,
        entropy_gate_threshold=entropy_gate_threshold,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    # Position is decided using info available at close of day i; apply next-day return.
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

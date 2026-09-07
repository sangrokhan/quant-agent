"""Strategy: SMA trend breakout gated by a positive-rolling-skewness regime.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-055):
Per pfolio.io's return-skewness explainer: positive return skewness means
frequent small losses with occasional large gains (right-tail heavy) --
structurally the same payoff profile as trend-following. Negative skewness
(frequent small gains, occasional large losses) matches mean-reversion/
option-selling payoffs instead. This strategy tests the standard quant
heuristic mapping directly: gate a simple SMA trend breakout to trade ONLY
when the recent rolling skewness of daily returns is positive (or above a
threshold), on the theory that trend-following edge concentrates in periods
where the market's return distribution itself exhibits trend-like
(positive-skew) asymmetry. First skewness-based construction in this repo.

Signal logic
------------
- Rolling skewness of daily log returns over skew_window bars (standard
  bias-corrected sample skewness formula).
- "Positive-skew regime" = rolling skewness >= skew_threshold (default 0.0).
- Entry (long): close > SMA(trend_window) (simple trend breakout) AND in a
  positive-skew regime.
- Exit: close falls below SMA(trend_window) (trend break), OR the skew
  regime flips negative (risk-off exit), OR after max_hold_days trading
  days.
- Flat (no position) whenever not in an active long.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    skew_window: int = 60,
    skew_threshold: float = 0.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)

    rolling_skew = daily_log_ret.rolling(skew_window).skew()
    positive_skew_regime = rolling_skew >= skew_threshold

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    entry = trend_up & positive_skew_regime.fillna(False)
    exit_trend_break = ~trend_up
    exit_regime_flip = ~positive_skew_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_break.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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

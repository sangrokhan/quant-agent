"""Strategy: Plain (single-leg) Price Rate of Change zero-line crossover,
gated by a long-term trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-092):
Per QuantifiedStrategies.com's "Price Rate of Change Strategy (ROC
Indicator – Trading Rules and Backtest, Performance)"
(https://www.quantifiedstrategies.com/rate-of-change-trading-strategy/,
visited 2026-09-11), source's own disclosed rule: "Buy when ROC crosses
from negative to positive: indicating accelerating prices. Sell or short
when ROC crosses from positive to negative: indicating weakening prices."
ROC(n) = 100 * (close[t] - close[t-n]) / close[t-n], a plain single-leg
momentum oscillator. This is distinct from every prior repo ROC-based
indicator (Coppock Curve, KST), which are all multi-leg WEIGHTED
COMPOSITES of several different-period ROCs smoothed together -- this is
the first plain single-period ROC zero-cross test in the repo. Source's
own cons note ("can generate false signals in sideways or choppy markets
... best used with filters or additional rules e.g. trend confirmation")
motivates adding a long-term SMA trend filter (long-only, per repo/SAFETY
convention) rather than testing the raw unconditional zero-cross.

Signal logic
------------
- ROC(roc_window) = pct change of close vs `roc_window` bars ago (%).
- Entry (long): ROC crosses from <=0 to >0 (bullish momentum) AND close is
  above its `trend_window`-day SMA (established uptrend, avoids whipsaws
  per source's own stated weakness).
- Exit: ROC crosses back below 0, OR the trend filter breaks (close drops
  below the trend SMA), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    roc_window: int = 12,
    trend_window: int = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    roc = 100.0 * (close - close.shift(roc_window)) / close.shift(roc_window)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    bullish_cross = (roc > 0) & (roc.shift(1) <= 0)
    entry = bullish_cross & uptrend.fillna(False)
    exit_roc_flip = roc < 0
    exit_trend_break = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_roc_flip.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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

"""Strategy: plain PPO zero-line crossover trend-following (long-only, no
signal line involved).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-085):
Per StockCharts.com's PPO article ("A bullish trend signal occurs when the
PPO crosses above zero, while a bearish trend signal occurs when the PPO
crosses below zero") and cTrader Help's confirming description, the PPO's
plain ZERO-LINE crossover (fast EMA crossing above slow EMA, expressed as a
percentage) is itself a tradeable trend signal. This is DISTINCT from both
prior PPO strategies tested in this repo: 2026-09-04-109 (signal-line cross
confirmed by zero-line, entry trigger is the SIGNAL-LINE cross) and
2026-09-09-069 (histogram pullback-reexpansion pattern) -- neither uses the
raw zero-line cross itself as the entry trigger.

Signal logic
------------
- PPO = 100 * (EMA(fast_span) - EMA(slow_span)) / EMA(slow_span).
- Entry (long): PPO crosses from <=0 to >0 (fresh bullish cross).
- Exit: PPO crosses back below 0, OR a max_hold_days time-stop.
- Flat otherwise; long-only, no shorting (per SAFETY.md).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ppo(close: pd.Series, fast_span: int, slow_span: int) -> pd.Series:
    fast_ema = close.ewm(span=fast_span, adjust=False, min_periods=fast_span).mean()
    slow_ema = close.ewm(span=slow_span, adjust=False, min_periods=slow_span).mean()
    return 100.0 * (fast_ema - slow_ema) / slow_ema.replace(0, pd.NA)


def generate_signals(
    price_df: pd.DataFrame,
    fast_span: int = 12,
    slow_span: int = 26,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ppo = _ppo(close, fast_span, slow_span)
    prev_ppo = ppo.shift(1)
    bullish_cross = (ppo > 0) & (prev_ppo <= 0)
    bearish_cross = (ppo < 0) & (prev_ppo >= 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(bearish_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(bullish_cross.iloc[i]):
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

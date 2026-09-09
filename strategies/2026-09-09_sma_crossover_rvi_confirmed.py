"""Strategy: Fast/slow SMA crossover, confirmed by Dorsey's Relative
Volatility Index (RVI) > 50 (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-080):
Per a Scribd-hosted RVI trading-rules document (surfaced via Google search
snippet, browser_exec fallback -- web_search DDGS backend errored this
iteration), Donald Dorsey's own published six-rule RVI system explicitly
states: "Only take buy signals from moving average crossover when RVI>50."
This uses RVI purely as a CONFIRMATION GATE on a separate SMA crossover
signal, rather than as the standalone midline-crossover trigger itself (the
already-accepted 2026-09-05-003 variant, which buys when RVI ITSELF crosses
above 50). This tests whether Dorsey's originally-intended use case (a
volatility-direction filter on an independent trend-crossover system)
outperforms treating RVI as the entry trigger directly.

Signal logic
------------
- RVI(rvi_period): Dorsey's Relative Volatility Index (RSI-shaped formula
  fed the standard deviation of close prices split into up/down buckets).
- SMA crossover: fast_window SMA crosses above slow_window SMA (classic
  golden-cross-style signal).
- Entry (long): fresh SMA bullish cross AND RVI > 50 at that bar (Dorsey's
  own confirmation gate).
- Exit: SMA bearish cross (fast crosses back below slow), OR RVI drops
  below 40 (Dorsey's own published exit threshold, reused here), OR a
  max_hold_days time-stop.
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


def _rvi(df: pd.DataFrame, period: int = 10) -> pd.Series:
    """Dorsey's Relative Volatility Index."""
    close = df["close"]
    std = close.rolling(period).std()
    diff = close.diff()

    up_std = std.where(diff > 0, 0.0)
    down_std = std.where(diff < 0, 0.0)

    up_avg = up_std.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    down_avg = down_std.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    rs = up_avg / down_avg.replace(0, pd.NA)
    rvi = 100.0 - (100.0 / (1.0 + rs))
    return rvi


def generate_signals(
    price_df: pd.DataFrame,
    rvi_period: int = 10,
    fast_window: int = 20,
    slow_window: int = 50,
    rvi_confirm_level: float = 50.0,
    rvi_exit_level: float = 40.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rvi = _rvi(df, rvi_period)
    fast_sma = close.rolling(fast_window).mean()
    slow_sma = close.rolling(slow_window).mean()

    prev_fast, prev_slow = fast_sma.shift(1), slow_sma.shift(1)
    bullish_cross = (fast_sma > slow_sma) & (prev_fast <= prev_slow)
    bearish_cross = (fast_sma < slow_sma) & (prev_fast >= prev_slow)
    confirmed = rvi > rvi_confirm_level

    entry = bullish_cross & confirmed.fillna(False)
    exit_rvi_weak = rvi < rvi_exit_level

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(bearish_cross.iloc[i]) or bool(exit_rvi_weak.iloc[i]) or held >= max_hold_days:
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

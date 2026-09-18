"""Strategy: The Rubber Band Strategy (ATR-band mean reversion) + a
min_hold_days no-exit-before-N-days gate (rescue attempt for near-miss
id 2026-09-11-074).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-006):
Direct fix for prior rejection 2026-09-11-074 (Rubber Band Strategy, per
https://www.quantifiedstrategies.com/quantitative-trading-strategies/):
the fine-tuned QQQ config (range_window=3, high_window=7, band_mult=2.0)
cleared Sharpe (1.387), MDD (0.131), and walk-forward (1.0) but
decisively FAILED transaction-cost survival (net Sharpe 0.451 vs 0.5
threshold, ~788 trades over 14yr / ~56 trades/year -- too much churn from
the immediate "close crosses above yesterday's high" exit trigger).

This sub-iteration adds an explicit `min_hold_days` gate that suppresses
the exit signal for the first N days after entry (the SAME fix pattern
already used successfully elsewhere in this repo to rescue TC-survival
failures, e.g. Klinger Volume Oscillator 2026-09-04-085, ZLEMA/EMA
2026-09-06-171, Accelerator Oscillator 2026-09-06-174) -- keeping the
entry logic and the underlying "exit above yesterday's high" mechanic
identical to 2026-09-11-074's own code otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} long/flat)
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
    range_window: int = 3,
    high_window: int = 7,
    band_mult: float = 2.0,
    min_hold_days: int = 3,
    trend_gate: bool = False,
    fast_sma: int = 50,
    slow_sma: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Identical Rubber Band band-touch entry as 2026-09-11-074, but the
    "close above yesterday's high" exit trigger is suppressed for the
    first `min_hold_days` days after entry (reduces trade churn/count to
    address the TC-survival failure).
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    avg_range = (high - low).rolling(range_window).mean()
    rolling_high = high.rolling(high_window).max()
    band = rolling_high - band_mult * avg_range

    entry = close < band
    if trend_gate:
        sma_fast = close.rolling(fast_sma).mean()
        sma_slow = close.rolling(slow_sma).mean()
        entry = entry & (sma_fast > sma_slow).fillna(False)

    prior_high = high.shift(1)
    exit_signal = (close > prior_high).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_days = 0
    for i in range(len(close)):
        if in_position:
            hold_days += 1
            if hold_days >= min_hold_days and bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if pd.notna(entry.iloc[i]) else False:
                in_position = True
                hold_days = 0
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

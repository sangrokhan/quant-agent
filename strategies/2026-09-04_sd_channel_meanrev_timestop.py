"""Strategy: Standard Deviation Channel mean-reversion, SMA(200) trend
filter, mean-touch/time-stop exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-046):
Per a Google AI-overview synthesis (Quantvero-sourced "Quantified Strategy
Rules"): a 20-period SMA baseline with +/-2.0 standard-deviation channel
bands identifies overextended price. Long entry: close below the lower
-2.0 SD band AND close above SMA(200) (broader uptrend filter, ensuring
pullbacks are bought within an uptrend rather than a falling market).
Exit: price touches the middle band (SMA20, the statistical mean target)
OR a fixed time-stop (exit unconditionally after max_hold_days if the
mean target hasn't been reached). Distinct exit mechanic from prior
Bollinger-Band mean-reversion attempts in this repo (2026-09-03-001,
-023), which exited purely on a regime/gate condition breaking rather
than a price target + time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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
    sd_window: int = 20,
    sd_mult: float = 2.0,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(sd_window).mean()
    std = close.rolling(sd_window).std()
    lower_band = sma - sd_mult * std
    sma_trend = close.rolling(trend_window).mean()

    below_lower = close < lower_band
    trend_ok = (close > sma_trend).fillna(False)
    entry_signal = below_lower.fillna(False) & trend_ok

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = None
    for i in range(len(close)):
        if in_position:
            days_held = i - entry_idx
            mean_touched = close.iloc[i] >= sma.iloc[i] if pd.notna(sma.iloc[i]) else False
            if mean_touched or days_held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                entry_idx = None
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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

"""Strategy: Daily Pivot Point (P) breakout, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-073):
Per ProTradingSchool's Pivot Points strategy guide: the classic floor-trader
pivot point P = (prev_high + prev_low + prev_close) / 3 (plus derived
R1/R2/R3/S1/S2/S3 levels) acts as a level many traders watch; a close
crossing decisively above the pivot point signals a new uptrend emerging
worth a long entry (the source's "pivot level breakout" strategy family,
as opposed to the more discretionary pullback-reversal family which needs
subjective trend-line/candlestick confirmation not implementable here).
Exit when close crosses back below the pivot point. First strategy in this
repo using NO rolling window/smoothing at all -- purely the single prior
bar's H/L/C combined algebraically, recomputed fresh each bar.

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


def _pivot_level(df: pd.DataFrame, level: str = "P") -> pd.Series:
    """Compute the requested classic floor-trader pivot level from the
    PRIOR bar's high/low/close (shifted by 1 so no lookahead)."""
    prev_high = df["high"].shift(1)
    prev_low = df["low"].shift(1)
    prev_close = df["close"].shift(1)

    pivot = (prev_high + prev_low + prev_close) / 3.0
    if level == "P":
        return pivot
    elif level == "R1":
        return (2 * pivot) - prev_low
    elif level == "S1":
        return (2 * pivot) - prev_high
    elif level == "R2":
        return pivot + (prev_high - prev_low)
    elif level == "S2":
        return pivot - (prev_high - prev_low)
    else:
        raise ValueError(f"Unsupported pivot level: {level}")


def generate_signals(
    price_df: pd.DataFrame,
    entry_level: str = "P",
    exit_level: str = "P",
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: close crosses above ``entry_level`` (from below).
    Exit: close crosses below ``exit_level`` (from above).
    """
    df = _prep(price_df)
    close = df["close"]

    entry_pivot = _pivot_level(df, entry_level)
    exit_pivot = _pivot_level(df, exit_level)

    cross_up = (close > entry_pivot) & (close.shift(1) <= entry_pivot.shift(1))
    cross_down = (close < exit_pivot) & (close.shift(1) >= exit_pivot.shift(1))

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if bool(cross_down.iloc[i]) if not pd.isna(cross_down.iloc[i]) else False:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]) if not pd.isna(cross_up.iloc[i]) else False:
                in_position = True
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

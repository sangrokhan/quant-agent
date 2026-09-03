"""Strategy: Chande Momentum Oscillator (CMO) oversold-reversal, trend-filtered.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-055):
Per Google AI-overview synthesis of Quantified Strategies/TradingSim/
GoCharting: the Chande Momentum Oscillator (CMO, Tushar Chande) is a
symmetric (-100..+100) momentum oscillator, distinct from RSI's
ratio-based construction -- CMO uses the raw difference of up/down sums
normalized by their total. Standard rule: long entry when CMO crosses
below an oversold threshold (-50) then turns back up (reversal, not a
straight threshold-cross), exit when CMO crosses above an overbought
threshold (+50) or after a fixed time stop; optional 200-day SMA trend
filter to only take longs when price is above the long-term trend.

CMO formula (standard, Chande):
    diff = close.diff()
    up_sum = diff.clip(lower=0).rolling(window).sum()
    down_sum = (-diff.clip(upper=0)).rolling(window).sum()
    CMO = 100 * (up_sum - down_sum) / (up_sum + down_sum)

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


def _cmo(close: pd.Series, window: int = 9) -> pd.Series:
    diff = close.diff()
    up_sum = diff.clip(lower=0).rolling(window).sum()
    down_sum = (-diff.clip(upper=0)).rolling(window).sum()
    total = up_sum + down_sum
    cmo = 100.0 * (up_sum - down_sum) / total.replace(0, pd.NA)
    return cmo.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    cmo_window: int = 9,
    oversold_threshold: float = -50.0,
    overbought_threshold: float = 50.0,
    trend_window: int = 200,
    max_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cmo = _cmo(close, window=cmo_window)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    # Oversold reversal: CMO was below the oversold threshold on the prior
    # bar and has now turned back up (crossed back above it).
    was_oversold = cmo.shift(1) < oversold_threshold
    entry_signal = was_oversold & (cmo >= oversold_threshold) & uptrend.fillna(False)
    exit_signal = cmo > overbought_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_days = 0
    for i in range(len(close)):
        if in_position:
            hold_days += 1
            if bool(exit_signal.iloc[i]) or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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

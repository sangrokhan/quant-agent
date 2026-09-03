"""Strategy: Elder's Force Index dual-EMA pullback entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-049):
Per a Google AI-overview synthesis (Finlogix/LuxAlgo/TradingView et al.):
Dr. Alexander Elder's Force Index (EFI) combines price change, direction,
and volume into a single value: Raw Force Index = (close - prev_close) *
volume. A long-term EMA (13-period) of the raw value determines the
dominant trend direction (positive = bull); a short-term EMA (2-period)
times exact pullback entries -- while the 13-period EFI stays positive,
wait for the 2-period EFI to dip below zero (a brief pause in buying
pressure) then cross back above zero as the buy trigger. First Force
Index (raw signed price-change magnitude * volume, distinct from every
prior volume indicator already tested -- OBV/CMF/A-D all discard the
magnitude of the price change, using only its sign or intrabar
positioning) strategy tested in this repo.

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
    short_window: int = 2,
    long_window: int = 13,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    raw_efi = close.diff() * volume
    efi_short = raw_efi.ewm(span=short_window, adjust=False).mean()
    efi_long = raw_efi.ewm(span=long_window, adjust=False).mean()

    bull_trend = efi_long > 0
    was_below_zero = efi_short.shift(1) < 0
    recovery_cross = (efi_short >= 0) & was_below_zero.fillna(False)

    entry = recovery_cross & bull_trend
    stay = bull_trend  # exit when the long-term trend filter turns negative

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if not bool(stay.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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

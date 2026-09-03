"""Strategy: Detrended Price Oscillator (DPO) zero-line cycle cross.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-056):
Per Google AI-overview synthesis (QuantifiedStrategies' own DPO article
404'd; TradingView/GoCharting corroborate the core formula/rule): the
Detrended Price Oscillator isolates cyclical price structure by
subtracting a BACKWARD-SHIFTED simple moving average from price -- a
fundamentally different construction from every prior oscillator in this
repo (all others use either a raw price-range ratio or a forward-looking
smoothing constant, none deliberately shift the baseline back in time to
strip the trend component while preserving cycle timing).

DPO formula (standard):
    shift = N // 2 + 1
    SMA_N = close.rolling(N).mean()
    DPO_t = close_t - SMA_N[t - shift]   (i.e. SMA_N.shift(shift))

Trading rule (mechanically-testable simplification of the source's
trough/peak-reversal rule): long entry when DPO crosses above zero from
below (proxy for "DPO reaches a trough below zero and turns upward"),
exit when DPO crosses back below zero (proxy for "DPO peaks and rolls
over"). No short side (long-only per repo convention).

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


def _dpo(close: pd.Series, window: int = 20) -> pd.Series:
    shift = window // 2 + 1
    sma = close.rolling(window).mean()
    return close - sma.shift(shift)


def generate_signals(
    price_df: pd.DataFrame,
    dpo_window: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    dpo = _dpo(close, window=dpo_window)
    entry_signal = (dpo > 0) & (dpo.shift(1) <= 0)
    exit_signal = (dpo < 0) & (dpo.shift(1) >= 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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

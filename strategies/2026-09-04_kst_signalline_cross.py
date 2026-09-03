"""Strategy: Know Sure Thing (KST) oscillator signal-line cross near zero.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-057):
Per QuantifiedStrategies' KST Oscillator article (Martin Pring): the KST
is a weighted sum of 4 SMA-smoothed rate-of-change (ROC) values of
different periods, plus a 9-period SMA signal line. Standard params: ROC
periods 10/15/20/30, smoothed by SMA 10/10/10/15, weighted x1/x2/x3/x4.
Concrete general rule (specific numeric backtest rule paywalled): KST
crossing above its signal line while near/below the zero centerline
(oversold-momentum recovery) signals rising upside momentum; exit on the
opposite (KST crosses back below signal line).

KST formula (standard, Martin Pring):
    ROC_i(n) = 100 * (close / close.shift(n) - 1)
    RCMA_i = SMA(ROC_i(roc_period_i), sma_period_i)
    KST = sum(weight_i * RCMA_i)
    signal = SMA(KST, signal_period)

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


def _kst(close: pd.Series, signal_period: int = 9) -> tuple[pd.Series, pd.Series]:
    roc_periods = [10, 15, 20, 30]
    sma_periods = [10, 10, 10, 15]
    weights = [1, 2, 3, 4]

    rcma_sum = pd.Series(0.0, index=close.index)
    for roc_p, sma_p, w in zip(roc_periods, sma_periods, weights):
        roc = 100.0 * (close / close.shift(roc_p) - 1.0)
        rcma = roc.rolling(sma_p).mean()
        rcma_sum = rcma_sum + w * rcma

    signal = rcma_sum.rolling(signal_period).mean()
    return rcma_sum, signal


def generate_signals(
    price_df: pd.DataFrame,
    signal_period: int = 9,
    centerline_threshold: float = 0.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    kst, signal = _kst(close, signal_period=signal_period)

    cross_up = (kst > signal) & (kst.shift(1) <= signal.shift(1))
    cross_down = (kst < signal) & (kst.shift(1) >= signal.shift(1))
    near_zero_or_below = kst <= centerline_threshold

    entry_signal = cross_up & near_zero_or_below
    exit_signal = cross_down

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

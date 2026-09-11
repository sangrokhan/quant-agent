"""Strategy: 2-period MFI extreme-oversold mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-076):
Per QuantifiedStrategies.com's disclosed rule
(https://www.quantifiedstrategies.com/quantitative-trading-strategies/,
visited this iteration): "If the two-day MFI is below 10, we buy at the
close. We sell at the close when the close ends higher than yesterday's
high. We have a time stop of 10 trading days." Source's own QQQ backtest:
average gain per trade 0.46%, win rate 70%, annual return 11.1% at 34%
time invested.

This is distinct from the already-tested MFI oversold-recovery strategy
(2026-09-04-033, rejected) which used a 14-period MFI with a 20-25
oversold threshold, a 200-day SMA trend gate, and a "cross back above
threshold" entry trigger -- a fundamentally different (longer-period,
trend-gated, threshold-recovery) construction. This strategy instead uses
an extremely short 2-period MFI (Larry-Connors-RSI2-style very-short-
lookback extreme), no trend gate, a raw "MFI<10" single-bar oversold
trigger (not a recovery-crossback), and a distinct exit rule (close above
yesterday's high, not a threshold cross) plus a fixed time stop.

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


def _mfi(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]
    typical_price = (high + low + close) / 3.0
    raw_money_flow = typical_price * volume
    tp_diff = typical_price.diff()

    pos_flow = raw_money_flow.where(tp_diff > 0, 0.0)
    neg_flow = raw_money_flow.where(tp_diff < 0, 0.0)

    pos_sum = pos_flow.rolling(window).sum()
    neg_sum = neg_flow.rolling(window).sum()

    money_flow_ratio = pos_sum / neg_sum.replace(0, 1e-12)
    mfi = 100 - (100 / (1 + money_flow_ratio))
    mfi = mfi.where(neg_sum > 0, 100.0)
    return mfi


def generate_signals(
    price_df: pd.DataFrame,
    mfi_window: int = 2,
    oversold_threshold: float = 10.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    mfi = _mfi(df, mfi_window)
    entry = mfi < oversold_threshold
    prior_high = high.shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_bounce = bool(close.iloc[i] > prior_high.iloc[i]) if pd.notna(prior_high.iloc[i]) else False
            if exit_bounce or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if pd.notna(entry.iloc[i]) else False:
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

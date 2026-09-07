"""Strategy: Larry Connors' R3 strategy (RSI(2) 3-consecutive-day decline pullback).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-087),
sourced from https://www.quantifiedstrategies.com/larry-connors-r3-strategy/
("Larry Connors' R3 Strategy (It Still Works)"). Concrete rules quoted from
the source (Connors' "High Probability ETF Trading", 2009, Ch.4):

    "Original Rules:
    1. The instrument is above its 200-day moving average.
    2. RSI(2) is below 10.
    3. RSI(2) has declined 3 days in a row."

    Exit rule (per the source's own backtest methodology): "buy ETFs on
    pullbacks, not breakouts" -- exit when momentum normalizes, matching
    this repo's existing Connors-RSI-family convention (RSI(2) mean
    reversion, 2026-09-03-005) of exiting on a recovery above a short SMA.

Distinct from the already-accepted plain Connors RSI(2) mean-reversion
(2026-09-03-005, single-day RSI(2)<=threshold trigger, no consecutive-decline
requirement) by requiring the ADDITIONAL "3 consecutive days of RSI(2)
decline" precondition -- Connors' own refinement meant to catch a
multi-day fading pullback rather than a single oversold spike.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int = 2) -> pd.Series:
    """Wilder's RSI (standard exponential smoothing, alpha=1/window)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    rsi_window: int = 2,
    rsi_threshold: float = 10.0,
    decline_days: int = 3,
    exit_sma_window: int = 5,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    rsi = _rsi(close, rsi_window)
    rsi_declining = pd.Series(True, index=close.index)
    for k in range(1, decline_days):
        rsi_declining &= rsi.shift(k - 1) < rsi.shift(k)

    exit_sma = close.rolling(exit_sma_window).mean()

    entry = uptrend.fillna(False) & (rsi < rsi_threshold) & rsi_declining.fillna(False)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = 0
    for i in range(n):
        if in_pos:
            held = i - entry_idx
            exit_signal = (
                not pd.isna(exit_sma.iloc[i]) and close.iloc[i] > exit_sma.iloc[i]
            )
            if exit_signal or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_pos = True
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

"""Strategy: Cutler's RSI (SMA-based RSI) oversold-recovery mean reversion,
trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-008):
Per QuantifiedStrategies.com's "Cutler's RSI Trading Strategy" article
(https://www.quantifiedstrategies.com/cutlers-rsi-trading-strategy/, read
via browser_exec after web_search DDGS/Yahoo backend errored with TLS
RequestError on every query attempted this iteration): Cutler's RSI is a
variation of Welles Wilder's RSI that uses a SIMPLE moving average of
up-moves/down-moves instead of Wilder's own smoothed (Wilder-style
recursive EMA) moving average. Cutler's own stated finding: because
Wilder's original RSI recursively depends on where in the data the
calculation starts ("Data Length Dependency"), his SMA-based variant gives
consistent results regardless of starting point. Same 30/70
oversold/overbought interpretation as classic RSI. This iteration tests
the oversold-recovery entry (Cutler's RSI dips below 30, then crosses back
above 30) gated by a longer-term SMA(trend_window) uptrend filter (the
same trend-confirmation pattern already validated for numerous other
oscillators in this repo), exit on RSI reaching overbought (70) or a
max_hold_days time-stop. First Cutler's RSI strategy in this repo --
distinct from every Wilder RSI, Connors RSI, Stochastic RSI, and Slow RSI
(Apirine) variant already tested, since Cutler's construction uses a
strict SMA (not any EMA/Wilder-smoothing variant) for both the
up-average and down-average terms.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cutlers_rsi(close: pd.Series, period: int) -> pd.Series:
    """Cutler's RSI: SMA of gains / (SMA of gains + SMA of losses) * 100,
    using a plain rolling SIMPLE moving average (not Wilder's recursive
    smoothed average) for both the up-average and down-average terms.
    """
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    denom = (avg_gain + avg_loss).replace(0.0, float("nan"))
    rsi = (avg_gain / denom) * 100.0
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    oversold_level: float = 30.0,
    overbought_level: float = 70.0,
    trend_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trend_up = close > close.rolling(trend_window).mean()
    rsi = _cutlers_rsi(close, rsi_period)

    oversold_recovery = (rsi > oversold_level) & (rsi.shift(1) <= oversold_level)
    overbought_exit = rsi >= overbought_level

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(overbought_exit.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(oversold_recovery.iloc[i]) and bool(trend_up.iloc[i]):
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

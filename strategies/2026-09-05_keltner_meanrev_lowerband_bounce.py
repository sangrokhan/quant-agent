"""Strategy: Keltner Channel mean-reversion (lower-band bounce), gated by a
longer-term uptrend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-074):
This repo has only tested Keltner Channel as a BREAKOUT signal
(2026-09-03-016: long when close breaks above the upper band) and as part
of TTM/LazyBear squeeze constructions (2026-09-04-091/126). The standard,
widely-documented MEAN-REVERSION interpretation of Keltner Channels --
distinct from the breakout interpretation of the same indicator -- treats a
close crossing below the lower band as an oversold bounce entry rather than
a trend continuation signal. Per multiple convergent community sources
(Facebook trading-community posts synthesized via Google search): "BUY
Signal: Price crosses below the Lower Band and bounces back -> Mean-
reversion buy" with exit "revert back from the ... bottom of the band to
the middle 20-period moving average" (the EMA basis). Gated here by a
longer-term SMA uptrend filter (standard convention in this repo for
oversold-bounce mean-reversion strategies, avoiding buying dips in a
structural downtrend) that the raw community rule did not explicitly
include.

Signal logic
------------
- Keltner Channel: basis = EMA(ema_window), band = ATR(atr_window) *
  atr_mult; lower_band = basis - band.
- Entry (long): close crosses below the lower band (touch/breach) AND
  close > SMA(trend_window) (longer-term uptrend gate).
- Exit: close crosses back above the EMA basis (mean-reversion target
  reached), the trend filter breaks, or a max_hold_days time-stop.

Interface contract (RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 20,
    atr_window: int = 10,
    atr_mult: float = 2.0,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    basis = close.ewm(span=ema_window, adjust=False).mean()
    atr = _atr(df, atr_window)
    lower_band = basis - atr_mult * atr

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    below_lower = close < lower_band
    entry = below_lower & below_lower.shift(1).fillna(False).eq(False) & uptrend.fillna(False)
    # entry on the day close FIRST dips below the lower band (not every day
    # it stays below), to avoid re-entering every bar of a sustained breach.
    entry = below_lower & (~below_lower.shift(1).fillna(False)) & uptrend.fillna(False)

    exit_meanrev = close > basis
    exit_trend_break = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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

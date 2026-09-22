"""Strategy: Ehlers Center of Gravity (COG) Oscillator crossing its own EMA signal line.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-052):
Per QuantifiedStrategies.com's Center of Gravity Oscillator writeup
(https://www.quantifiedstrategies.com/center-of-gravity-oscillator/, read
via browser_exec this iteration -- web_search DDGS backend TLS-errored on
all queries), John Ehlers' COG indicator computes a weighted average of the
last `length` closes (COG = sum(price_i * weight_i) / sum(price_i), weight
decreasing linearly from most-recent=length down to 1), producing a
lag-reduced, price-scale oscillator. Source's own disclosed backtest rule:
"When the Center of Gravity Oscillator closes above its 20-day EMA, go
long; when it closes below, sell" (tested on GLD and Bitcoin in the
source's own writeup, GLD: 166 trades avg 0.96%/trade 51% win rate 29% MDD;
BTC: 119 trades avg 5.8%/trade 57% win rate 60% MDD). Implemented here
exactly as disclosed (always-in-market long/flat with the reverse leg
dropped since this repo is long-only per SAFETY.md) and grid-tested across
QQQ/SPY/BTC/ETH.

First Ehlers Center of Gravity oscillator strategy in this repo (0 prior
matches for "center of gravity"/"cog" in the knowledge base) -- distinct
from other Ehlers oscillators already tested (Fisher Transform, Reflex,
Trendflex, MESA Stochastic, EBSW, Synthetic Oscillator, RocketRSI, Elegant
Oscillator, Universal Oscillator, Cybernetic Oscillator) since none of those
use a simple weighted-average-of-price "center of gravity" construction --
COG is closer in spirit to a weighted-moving-average crossover than a
filtered/normalized cycle oscillator.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cog(close: pd.Series, length: int) -> pd.Series:
    weights = np.arange(length, 0, -1, dtype=float)  # most-recent bar gets weight=length
    weight_sum = weights.sum()

    def _window_cog(window: np.ndarray) -> float:
        # window is oldest->newest per pandas rolling.apply convention;
        # reverse so index 0 = most recent (matches source's Day1=most recent, weight=length)
        w = window[::-1]
        return float(np.dot(w, weights) / weight_sum)

    return close.rolling(length).apply(_window_cog, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    cog_length: int = 10,
    signal_ema_length: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cog = _cog(close, cog_length)
    signal = cog.ewm(span=signal_ema_length, min_periods=signal_ema_length, adjust=False).mean()

    position = (cog > signal).astype(int)
    position = position.fillna(0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

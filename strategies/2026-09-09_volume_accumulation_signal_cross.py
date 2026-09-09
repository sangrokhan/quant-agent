"""Strategy: Volume Accumulation (cumulative Volume x (Close - midpoint))
crossing above its own EMA signal line, gated by a long-term SMA uptrend
filter (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-081):
Per Commodity.com's Volume Accumulation formula (surfaced via browser_exec
after web_search DDGS returned degraded results this iteration, and after
the QuantifiedStrategies VAP article 404'd and MultiCharts was Cloudflare-
blocked): daily volume contribution = Volume x [Close - (High+Low)/2],
cumulatively summed, only assigning POSITIVE volume to a day when the close
finishes above the midpoint of that day's range (and negative when below).
This is an UNNORMALIZED distance-from-midpoint volume weighting, distinct
from every other volume-accumulation indicator already tested in this repo:
OBV (pure sign-of-price-change, no magnitude), AD Line / CMF (normalized
Close-Location-Value ratio in [-1,1]), PVT/VPT (weighted by pct price
change magnitude, not intrabar range position). Entry: cumulative Volume
Accumulation crosses above its own EMA signal line while price is in a
confirmed uptrend (close > SMA(trend_window)).

Signal logic
------------
- Daily contribution = Volume * (Close - (High+Low)/2).
- Volume Accumulation (VA) = cumulative sum of daily contributions.
- Signal line = EMA(VA, signal_span).
- Entry (long): VA crosses from <=signal to >signal (fresh bullish cross)
  AND close > SMA(trend_window) (uptrend confirmation).
- Exit: VA crosses back below its signal line, OR the trend filter breaks,
  OR a max_hold_days time-stop.
- Flat otherwise; long-only, no shorting (per SAFETY.md).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _volume_accumulation(df: pd.DataFrame) -> pd.Series:
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]
    midpoint = (high + low) / 2.0
    daily_contribution = volume * (close - midpoint)
    return daily_contribution.cumsum()


def generate_signals(
    price_df: pd.DataFrame,
    signal_span: int = 20,
    trend_window: int = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    va = _volume_accumulation(df)
    signal = va.ewm(span=signal_span, adjust=False, min_periods=signal_span).mean()
    sma = close.rolling(trend_window).mean()

    prev_va, prev_signal = va.shift(1), signal.shift(1)
    bullish_cross = (va > signal) & (prev_va <= prev_signal)
    bearish_cross = (va < signal) & (prev_va >= prev_signal)
    uptrend = close > sma

    entry = bullish_cross & uptrend.fillna(False)
    exit_trend_break = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(bearish_cross.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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

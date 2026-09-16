"""Strategy: Alexander Elder SafeZone Stop as a trailing-stop EXIT overlay on
a simple SMA-crossover trend-following ENTRY.

Hypothesis (this cron trigger's iteration 3):
Per Elder's SafeZone Stop (2002), confirmed via Google SERP synthesis this
iteration (QuantShare.com's own disclosed usage rule: "sell = close <
safezone(20, 2)" -- lookback=20, coefficient=2 are the source's own default
parameters; corroborated by Wealth-Lab Wiki and a TradingView SERP snippet:
"Long Stop = Previous Low - (Average Downside Noise x Multiplier)"), this
iteration operationalizes SafeZone as a trailing STOP-LOSS overlay (not an
entry trigger) on a simple SMA-crossover trend-following entry: entry when
close crosses above SMA(entry_window) (a fresh uptrend signal), held until
either (a) close drops below the SafeZone trailing stop level (source's own
disclosed sell rule, designed to filter out normal trend "noise" dips while
still catching genuine trend breaks) or (b) a max_hold_days backstop. This
is a genuinely new indicator family for this repo (0 prior SafeZone
entries) and a distinct construction from this repo's many other
trend-entry + volatility-stop combinations (e.g. Chandelier Exit, which
uses ATR off the highest-high rather than SafeZone's own downside-noise
statistic off consecutive lower-lows).

SafeZone construction (long side)
----------------------------------
- For each bar where low < prior day's low (a "downside penetration"),
  penetration = prior_low - low; bars where low >= prior_low contribute 0.
- Average Downside Noise = rolling mean of `penetration` over `lookback`
  bars (source default 20).
- SafeZone stop level = prior_low - coefficient * Average Downside Noise
  (source default coefficient=2, "generally traders use a value of 2 to 3").
- Exit rule (source's own disclosed usage): close < safezone_stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _safezone_stop(low: pd.Series, lookback: int, coefficient: float) -> pd.Series:
    prior_low = low.shift(1)
    penetration = (prior_low - low).clip(lower=0.0)
    avg_downside_noise = penetration.rolling(lookback).mean()
    stop = prior_low - coefficient * avg_downside_noise
    return stop


def generate_signals(
    price_df: pd.DataFrame,
    entry_window: int = 20,
    lookback: int = 20,
    coefficient: float = 2.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, low = df["close"], df["low"]

    sma = close.rolling(entry_window).mean()
    entry_signal = (close > sma) & (close.shift(1) <= sma.shift(1))

    stop_level = _safezone_stop(low, lookback, coefficient)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            stop_val = stop_level.iloc[i]
            stop_hit = bool(close.iloc[i] < stop_val) if not pd.isna(stop_val) else False
            if stop_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            entry_hit = bool(entry_signal.iloc[i]) if not pd.isna(entry_signal.iloc[i]) else False
            if entry_hit:
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

"""Strategy: Anchored Momentum (EMA/SMA ratio threshold crossover), long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-177):
Anchored Momentum (Rudy Stefenel, TASC 1998, popularized further by Ron
Rowland/AllStarInvestor) replaces the noisy two-point momentum calculation
(price_today - price_n_days_ago) with a smoother "anchor": momentum is
computed as the percentage difference between a fast EMA and a slower SMA of
closing prices, so today's price still drives the signal lag-free while the
reference point (the SMA) moves smoothly instead of jumping discretely each
day a stale data point rolls off the lookback window.

Per StockSharp's own coded strategy doc (the only source found this
iteration with an exact numeric threshold rule; the original TASC/Proactive
Advisor sources describe the construction only qualitatively):
  Momentum = EMA(ema_period, close) / SMA(sma_period, close) - 1
  Long entry: momentum crosses above up_level (source default 0.025 = 2.5%)
  Exit (source is long/short symmetric on 4h FX candles; this repo tests
    long-only per its no-short convention): exit when momentum crosses back
    below up_level, or a max_hold_days time-stop backstop (source has none).

Source periods (SmaPeriod=8, EmaPeriod=6) were tuned for 4h FX candles;
this repo grid-tests longer daily-bar-appropriate periods per the
Research Agent's own judgment since the source itself notes "any data
interval... and a wide range of periods (20, 50, 200, etc)" (per the
Proactive Advisor Magazine explainer).

First Anchored Momentum strategy in this repo -- distinct from all prior
EMA/SMA crossover strategies (which compare two lines' levels directly) and
all prior oscillator zero-line-cross strategies (which use a différence, not
a ratio/percentage) since this is a normalized ratio-threshold construction.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series {0,1} long/flat
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
    sma_period: int = 42,
    ema_period: int = 21,
    up_level: float = 0.025,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(sma_period).mean()
    ema = close.ewm(span=ema_period, min_periods=ema_period, adjust=False).mean()
    momentum = (ema / sma) - 1.0

    above_up = momentum > up_level

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if not bool(above_up.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(above_up.iloc[i]):
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

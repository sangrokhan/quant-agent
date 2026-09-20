"""Strategy: One-Day-Loss Magnitude-Scaled Reversal (single-symbol adaptation).

Hypothesis (see knowledge_base/strategies_log.jsonl):
Per QuantifiedStrategies.com's "One Day Loss Trading Strategy (1.73%
Overnight Returns)" (https://www.quantifiedstrategies.com/one-day-loss-
trading-strategy/), summarizing a 2003 academic study on short-term price
reversals after large one-day stock losses: the study's key finding is that
reversal-strategy returns SCALE with the magnitude of the event-day loss
(the bigger the single-day drop, the bigger the next-period rebound), is
stronger without concurrent news (not testable here, no news feed), and is
stronger with high event-day volume. This repo's data/loaders.py only
exposes single-symbol daily OHLCV (no cross-sectional stock universe), so
this is adapted to a single-symbol timing strategy: buy the SAME asset
(QQQ/SPY/BTC/ETH) after ITS OWN single-day return drops below a large
negative threshold (parameterized, since equity rarely sees the >10%
single-stock drops studied but crypto commonly does), optionally
conditioned on above-average volume (the source's own "high volume
amplifies the effect" finding), and hold for a short fixed period (the
source's own "sell at various points on the next trading day" is
approximated as a max_hold_days time-stop backstop, this repo's addition
since exact next-day exit timing isn't available on daily bars). Distinct
from all prior gap/RSI/IBS-based mean-reversion constructions in this repo
-- this is a pure one-day-return-magnitude threshold with a volume filter,
no oscillator.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    loss_threshold_pct: float = -0.05,
    volume_lookback: int = 20,
    require_high_volume: bool = True,
    volume_mult: float = 1.5,
    max_hold_days: int = 3,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_return = close.pct_change()

    loss_trigger = daily_return <= loss_threshold_pct

    if require_high_volume and "volume" in df.columns:
        avg_volume = df["volume"].rolling(volume_lookback, min_periods=volume_lookback).mean()
        high_volume = df["volume"] >= volume_mult * avg_volume
        entry_trigger = loss_trigger & high_volume
    else:
        entry_trigger = loss_trigger

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(df)):
        if not in_pos:
            if bool(entry_trigger.iloc[i]):
                in_pos = True
                hold_count = 0
        else:
            hold_count += 1
            if hold_count >= max_hold_days:
                in_pos = False
        position.iloc[i] = 1 if in_pos else 0

    return position.shift(1).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    loss_threshold_pct: float = -0.05,
    volume_lookback: int = 20,
    require_high_volume: bool = True,
    volume_mult: float = 1.5,
    max_hold_days: int = 3,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        loss_threshold_pct=loss_threshold_pct,
        volume_lookback=volume_lookback,
        require_high_volume=require_high_volume,
        volume_mult=volume_mult,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    return position * daily_returns

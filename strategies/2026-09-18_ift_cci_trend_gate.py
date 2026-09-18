"""Strategy: Inverse Fisher Transform of CCI (IFT-CCI), gated by SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id, this iteration):
John Ehlers' Inverse Fisher Transform compresses an oscillator's probability
distribution toward saturating +1/-1 extremes, producing sharper
buy/sell turning points than the raw oscillator. Applied to CCI (per
KivancOzbilgic's TradingView port, https://www.tradingview.com/script/HieaInXw/,
crediting John Ehlers): v1 = 0.1*CCI(close, cci_length), v2 = WMA(v1,
wma_length), IFT = (exp(2*v2)-1) / (exp(2*v2)+1). The indicator's own
reference lines are +0.5 (sell zone) and -0.5 (buy zone), corroborated by
FMZ's "WMA + IFT-CCI Momentum Filtering" multi-strategy write-up
(https://www.fmz.com/lang/en/strategy/500242): "Long trades are only
considered when the IFT-CCI value exceeds 0.5" (source uses it as a
momentum-confirmation filter on top of a WMA trend cross, not a standalone
trigger).

This repo's version: long entry when IFT-CCI crosses above buy_level
(default -0.5, the indicator's own "buy zone" boundary, an oversold-recovery
interpretation) while gated by a longer-term SMA(trend_window) uptrend
filter (this repo's established pattern for rescuing raw oscillator
crossovers, e.g. Vervoort RSI-IFT 2026-09-11-007/008); exit when IFT-CCI
crosses back below sell_level (default 0.5) or trend filter breaks, or a
max_hold_days time-stop.

First IFT-CCI strategy in this repo -- distinct construction basis from
already-rejected IFT-Stochastic (2026-09-06-114, applies IFT to a smoothed
Stochastic %K) and Vervoort RSI-IFT (2026-09-11-007/008, applies IFT to a
heavily pre-smoothed rainbow-weighted RSI) since this applies IFT directly
to a WMA-smoothed raw CCI.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cci(df: pd.DataFrame, window: int) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    sma = tp.rolling(window).mean()
    mad = tp.rolling(window).apply(lambda x: (x - x.mean()).abs().mean(), raw=False)
    return (tp - sma) / (0.015 * mad)


def _ift_cci(df: pd.DataFrame, cci_length: int, wma_length: int) -> pd.Series:
    import numpy as np

    cci = _cci(df, cci_length)
    v1 = 0.1 * cci
    weights = pd.Series(range(1, wma_length + 1), dtype=float)
    v2 = v1.rolling(wma_length).apply(
        lambda x: (x * weights.values).sum() / weights.sum(), raw=False
    )
    ift = (np.exp(2 * v2) - 1) / (np.exp(2 * v2) + 1)
    return ift


def generate_signals(
    price_df: pd.DataFrame,
    cci_length: int = 5,
    wma_length: int = 9,
    buy_level: float = -0.5,
    sell_level: float = 0.5,
    trend_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ift = _ift_cci(df, cci_length, wma_length)
    ift_prev = ift.shift(1)
    buy_cross = (ift_prev <= buy_level) & (ift > buy_level)
    sell_cross = (ift_prev >= sell_level) & (ift < sell_level)

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(sell_cross.iloc[i]) or not bool(uptrend.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(buy_cross.iloc[i]) and bool(uptrend.iloc[i]):
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

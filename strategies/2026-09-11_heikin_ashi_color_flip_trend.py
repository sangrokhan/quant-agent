"""Strategy: Heikin-Ashi candle color-flip trend following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-086):
Heikin-Ashi (HA) candles smooth raw OHLC into an averaged representation
whose "color" (haClose vs haOpen) tends to persist through sustained
trends and flip cleanly at trend exhaustion. Per QuantifiedStrategies.com's
own disclosed rule set (https://www.quantifiedstrategies.com/heikin-ashi-trading-strategy/,
backtested by the source on SPX monthly bars, 1960-present, 85 trades,
5.2% annual return vs 7.5% buy-and-hold, but with a favorable
asymmetric win/loss profile and max drawdown 29% vs 52.56% buy-and-hold):

    Buy  = Cross(haClose, haOpen)   # candle turns green (haClose crosses above haOpen)
    Sell = Cross(haOpen, haClose)   # candle turns red   (haClose crosses below haOpen)

haOpen is disclosed by the source as an EMA of the "total price"
(haClose) with a 10-period default (source explicitly states "we use a
10-day exponential average" and separately notes the general formula
Periods = (2/Multiplier) - 1 for a multiplier of 1/2 -> 3 periods, but the
strategy backtest itself uses the 10-period EMA convention). We adapt this
directly to a daily-bar test (source used monthly bars on SPX; this repo's
loaders only provide daily OHLCV) as a first pass, and grid-test whether
the standard HA-color-flip edge (if any) survives at daily granularity
across asset classes/vol regimes -- distinct from all previously-tested
indicator families (RSI/MACD/Bollinger/ADX/etc.) since this is the first
Heikin-Ashi-derived-candle strategy in this repo (candlestick technique
tag search returned 0 prior heikin_ashi entries).

Standard Heikin-Ashi recursive formulas:
    haClose_t = (Open_t + High_t + Low_t + Close_t) / 4
    haOpen_t  = (haOpen_{t-1} + haClose_{t-1}) / 2       (seeded haOpen_0 = (Open_0+Close_0)/2)
    haHigh_t  = max(High_t, haOpen_t, haClose_t)
    haLow_t   = min(Low_t,  haOpen_t, haClose_t)

The source additionally clarifies haOpen is well-approximated by an EMA of
haClose; we implement the exact recursive formula (more faithful to the
source's own stated definition) but expose ``ha_smooth`` as a no-op-esque
tunable for grid-test parameter-sensitivity purposes by instead applying an
optional additional EMA smoothing pass over the recursive haOpen/haClose
before generating the cross signal (ha_smooth=1 disables extra smoothing,
matching the pure recursive definition; ha_smooth>1 adds an EMA layer to
probe whether extra smoothing helps/hurts, addressing the source's own
noted risk that ha_smooth=1 can still whipsaw in choppy/sideways markets).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _heikin_ashi(df: pd.DataFrame, ha_smooth: int = 1) -> pd.DataFrame:
    """Compute Heikin-Ashi OHLC via the standard recursive formula.

    ha_smooth: if >1, apply an additional EMA(ha_smooth) smoothing pass to
    the recursive haClose/haOpen series before returning (probe of the
    source's alternate "EMA of total price" characterization of haOpen).
    """
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    ha_close = (o + h + l + c) / 4.0

    ha_open = pd.Series(index=df.index, dtype=float)
    ha_open.iloc[0] = (o.iloc[0] + c.iloc[0]) / 2.0
    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2.0

    if ha_smooth and ha_smooth > 1:
        ha_close = ha_close.ewm(span=ha_smooth, adjust=False).mean()
        ha_open = ha_open.ewm(span=ha_smooth, adjust=False).mean()

    ha_high = pd.concat([h, ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([l, ha_open, ha_close], axis=1).min(axis=1)

    return pd.DataFrame(
        {"ha_open": ha_open, "ha_close": ha_close, "ha_high": ha_high, "ha_low": ha_low},
        index=df.index,
    )


def generate_signals(
    price_df: pd.DataFrame,
    ha_smooth: int = 1,
    trend_sma_window: int = 0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    trend_sma_window=0 disables the optional close>SMA trend filter
    (source's plain "trend following" variant used no extra filter beyond
    the HA color flip itself); >0 requires close above that SMA as an
    additional long-only trend confirmation, since the source separately
    notes HA "produce[s] false signals in sideways or choppy markets" and
    recommends combining with a trend filter.
    """
    df = _prep(price_df)
    close = df["close"]
    ha = _heikin_ashi(df, ha_smooth=ha_smooth)

    green = ha["ha_close"] > ha["ha_open"]
    buy = green & (~green.shift(1).fillna(False))
    sell = (~green) & (green.shift(1).fillna(False))

    if trend_sma_window and trend_sma_window > 0:
        sma = close.rolling(trend_sma_window).mean()
        trend_ok = close > sma
    else:
        trend_ok = pd.Series(True, index=close.index)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(sell.iloc[i]) or held >= max_hold_days or not bool(trend_ok.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(buy.iloc[i]) and bool(trend_ok.iloc[i]):
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

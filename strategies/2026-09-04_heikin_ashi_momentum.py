"""Strategy: Heikin Ashi consecutive-color momentum, EMA(100) trend-filtered.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-045):
Per a Google AI-overview synthesis (PyQuantLab Medium article et al.):
Heikin Ashi candles (a smoothed OHLC transform) reduce noise vs raw
candlesticks. A trend-following entry: price above EMA(100) (macro trend
filter) AND N consecutive Heikin Ashi candles of the same (bullish) color
signals strong directional momentum worth entering long. Exit on the
first opposite-color Heikin Ashi candle (color-flip exit) -- simpler than
the source's compound no-wick+ATR-trailing-stop rule, isolating the core
HA-momentum signal (consistent with this repo's convention of testing a
simplified core mechanism when a source gives an elaborate multi-condition
rule).

Heikin Ashi formulas (standard):
    HA_close = (O + H + L + C) / 4
    HA_open  = (prev HA_open + prev HA_close) / 2   (first bar: (O+C)/2)
    HA_high  = max(H, HA_open, HA_close)
    HA_low   = min(L, HA_open, HA_close)
"Bullish" HA candle: HA_close > HA_open.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    ha_close = (o + h + l + c) / 4.0

    ha_open = pd.Series(index=df.index, dtype=float)
    ha_open.iloc[0] = (o.iloc[0] + c.iloc[0]) / 2.0
    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2.0

    ha_high = pd.concat([h, ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([l, ha_open, ha_close], axis=1).min(axis=1)

    return pd.DataFrame({"ha_open": ha_open, "ha_close": ha_close,
                          "ha_high": ha_high, "ha_low": ha_low}, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    consecutive_count: int = 3,
    ema_window: int = 100,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ha = _heikin_ashi(df)
    bullish = ha["ha_close"] > ha["ha_open"]
    bearish = ~bullish

    # Fresh entry trigger: exactly `consecutive_count` consecutive bullish
    # HA candles just completed (i.e. bullish now and for the prior
    # consecutive_count-1 bars, but NOT bullish consecutive_count+1 bars
    # ago -- avoids re-triggering every bar of a long green run).
    run_length = bullish.groupby((bullish != bullish.shift(1)).cumsum()).cumcount() + 1
    run_length = run_length.where(bullish, 0)
    fresh_trigger = (run_length == consecutive_count)

    ema_trend = close.ewm(span=ema_window, adjust=False).mean()
    trend_ok = (close > ema_trend).fillna(False)

    entry = fresh_trigger & trend_ok
    exit_signal = bearish  # color-flip exit: any bearish HA candle exits

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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

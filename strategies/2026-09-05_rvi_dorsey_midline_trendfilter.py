"""Strategy: Relative Volatility Index (RVI, Donald Dorsey) midline-cross
with the original numeric confirmation-escalation rule, gated by a long-term
trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-003):
The Relative Volatility Index (Donald Dorsey) is computed exactly like the
RSI, except it feeds in the standard deviation of high/low prices over a
rolling window (split into "up" and "down" stdev series based on whether
close rose or fell vs the prior bar) instead of price changes -- a measure
of *which direction* volatility is concentrated in, not raw price momentum.
Per Dorsey's own published rule (captured via TradingSim's RVI article,
2011), the mechanical buy/sell rule is: buy when RVI crosses above 50 (or,
if that signal was missed, buy when RVI crosses above 60 as a stronger
late-confirmation signal); close the long when RVI falls below 40. This is
tested here gated by a long-term uptrend filter (close above its own
trend-window SMA) since Dorsey's own explicit guidance is that RVI is "not
meant to be used as a standalone indicator" but as a confirmation layer for
other trend signals. First Relative Volatility Index (Dorsey volatility-
direction family) strategy in this repo -- distinct from Mass Index
(2026-09-04-075, also Dorsey, but a range-widening/narrowing gauge rather
than a directional-volatility oscillator) and from ATR/Bollinger-Band-based
volatility measures already tested.

Signal logic
------------
- up_stdev_t = std(close, rvi_window) if close_t > close_{t-1} else 0
- down_stdev_t = std(close, rvi_window) if close_t <= close_{t-1} else 0
- RVI = 100 * EMA(up_stdev, rvi_smooth) / (EMA(up_stdev, rvi_smooth) +
  EMA(down_stdev, rvi_smooth))
- trend_filter: close > close.rolling(trend_window).mean()
- Entry (long): RVI crosses above buy_threshold (50, Dorsey's primary
  signal) AND trend_filter is true.
- Exit: RVI drops below exit_threshold (40, Dorsey's own close-long rule),
  OR trend_filter flips false, OR a max_hold_days time-stop backstop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _relative_volatility_index(
    close: pd.Series, rvi_window: int, rvi_smooth: int
) -> pd.Series:
    stdev = close.rolling(rvi_window, min_periods=max(2, rvi_window // 2)).std()
    up_move = close.diff() > 0
    up_stdev = stdev.where(up_move, 0.0)
    down_stdev = stdev.where(~up_move, 0.0)

    up_ema = up_stdev.ewm(span=rvi_smooth, adjust=False).mean()
    down_ema = down_stdev.ewm(span=rvi_smooth, adjust=False).mean()

    denom = (up_ema + down_ema).replace(0.0, pd.NA)
    rvi = 100.0 * up_ema / denom
    return rvi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    rvi_window: int = 10,
    rvi_smooth: int = 14,
    buy_threshold: float = 50.0,
    exit_threshold: float = 40.0,
    trend_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rvi = _relative_volatility_index(close, rvi_window, rvi_smooth)
    trend_ma = close.rolling(trend_window, min_periods=max(5, trend_window // 5)).mean()
    trend_ok = close > trend_ma

    rvi_above_buy = rvi > buy_threshold
    entry_cross = rvi_above_buy & (~rvi_above_buy.shift(1).fillna(False))
    entry = entry_cross & trend_ok.fillna(False)

    exit_signal = (rvi < exit_threshold) | (~trend_ok.fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret

"""Strategy: Money Flow Index (MFI) 50-centerline crossover used as a
momentum-bias regime filter, confirmed by a long-term SMA trend filter
(long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-078):
Per TradingView's own MFI documentation (50-Line Crossover mode, surfaced
via Google search snippet -- "Crossover above 50 -> shift from bearish to
bullish money flow, potential trend [continuation]"), MFI (a volume-weighted
RSI analog) crossing above its 50 centerline signals a durable shift toward
bullish money flow, distinct from every prior MFI strategy in this repo
(oversold-bounce threshold 2026-09-04-033, %B+MFI thrust-confirmation
2026-09-05-011, bullish divergence 2026-09-05-061, MA-of-MFI cross
2026-09-06-129 -- none of which use the plain 50-centerline itself as the
entry trigger). Combined with a 200-day SMA long-term uptrend filter
(standard repo convention for centerline/zero-line momentum signals) to
avoid trading centerline noise in a structural downtrend.

Signal logic
------------
- MFI(mfi_period), standard typical-price x volume positive/negative money
  flow ratio construction.
- Entry (long): MFI crosses from <=50 to >50 AND close > SMA(trend_window)
  (uptrend confirmation).
- Exit: MFI crosses back below 50, OR close crosses below SMA(trend_window)
  (trend filter breaks), OR a max_hold_days time-stop backstop.
- Flat otherwise; long-only, no shorting (per SAFETY.md).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid).
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


def _mfi(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]
    typical_price = (high + low + close) / 3.0
    raw_money_flow = typical_price * volume

    tp_diff = typical_price.diff()
    positive_flow = raw_money_flow.where(tp_diff > 0, 0.0)
    negative_flow = raw_money_flow.where(tp_diff < 0, 0.0)

    positive_sum = positive_flow.rolling(period).sum()
    negative_sum = negative_flow.rolling(period).sum().replace(0, np.nan)

    money_ratio = positive_sum / negative_sum
    mfi = 100.0 - (100.0 / (1.0 + money_ratio))
    return mfi


def generate_signals(
    price_df: pd.DataFrame,
    mfi_period: int = 14,
    trend_window: int = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    mfi = _mfi(df, mfi_period)
    sma = close.rolling(trend_window).mean()

    prev_mfi = mfi.shift(1)
    bullish_cross = (mfi > 50) & (prev_mfi <= 50)
    bearish_cross = (mfi < 50) & (prev_mfi >= 50)
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

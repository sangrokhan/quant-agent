"""Strategy: MHL (Middle-High-Low) Moving Average crossover (Vitali Apirine,
TASC Aug 2016).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-136):
Per Vitali Apirine's "The Middle-High-Low Moving Average" (TASC Aug 2016;
TradeStation EasyLanguage code disclosed at
https://traders.com/Documentation/FEEDbk_docs/2016/08/TradersTips.html),
the MHL series is the midpoint of the mhl_length-day high/low range
(MHL = (Highest(High,N) + Lowest(Low,N)) / 2), then smoothed by a
moving_avg_length-period moving average (SMA or EMA). A traditional
close-based moving average of the same length and type is computed in
parallel. The source's own mechanical rule (disclosed in the TradeStation
Strategy code): go long when the close-based average crosses over the
MHL-based average, short when it crosses under. This repo trades long-only
per SAFETY.md, so the short signal becomes a flat/exit signal instead.

Signal logic
------------
- mhl = (rolling max(high, mhl_length) + rolling min(low, mhl_length)) / 2.
- avg_type "sma" or "ema" (source's AvgType switch): mhl_avg = MA(mhl,
  moving_avg_length); price_avg = MA(close, moving_avg_length), same MA
  type for both series (source computes SMA and EMA versions in parallel
  and lets a switch select one; this iteration parametrizes that choice).
- Entry (long): price_avg crosses over mhl_avg (source's own bullish
  trigger, "AvgValue crosses over MHLValue").
- Exit: price_avg crosses back under mhl_avg (source's own bearish trigger,
  translated to flat/exit rather than a short), OR max_hold_days time-stop.
- Flat otherwise.

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


def _moving_avg(series: pd.Series, length: int, avg_type: str) -> pd.Series:
    if avg_type == "ema":
        return series.ewm(span=length, adjust=False).mean()
    return series.rolling(length).mean()


def generate_signals(
    price_df: pd.DataFrame,
    mhl_length: int = 10,
    moving_avg_length: int = 50,
    avg_type: str = "sma",
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    mhl = (high.rolling(mhl_length).max() + low.rolling(mhl_length).min()) / 2.0
    mhl_avg = _moving_avg(mhl, moving_avg_length, avg_type)
    price_avg = _moving_avg(close, moving_avg_length, avg_type)

    cross_over = (price_avg > mhl_avg) & (price_avg.shift(1) <= mhl_avg.shift(1))
    cross_under = (price_avg < mhl_avg) & (price_avg.shift(1) >= mhl_avg.shift(1))

    entry = cross_over.fillna(False)
    exit_signal = cross_under.fillna(False)

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
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

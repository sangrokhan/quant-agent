"""Strategy: Chande Kroll Stop (CKS) breakout, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-116):
The Chande Kroll Stop (Tushar Chande & Stanley Kroll, 1994) is an ATR-based
pair of trailing stop lines: a "long stop" (below price, support in an
uptrend) and a "short stop" (above price, resistance in a downtrend).
Source (trendspider.com) gives the explicit formula and rule: a buy signal
fires when price crosses above BOTH stop lines (bullish breakout), a sell
signal fires when price falls below both lines. We implement this as a
long-only breakout-and-hold strategy: enter long when close crosses above
the (higher of the two) CKS lines, exit when close crosses back below the
long-stop line, or after a max_hold_days time-stop.

Formula
-------
- Initial high stop[i] = Highest(high, p)[i] - atr_mult * ATR(p)[i]
- Initial low stop[i]  = Lowest(low, p)[i]  + atr_mult * ATR(p)[i]
- Short stop[i] = Highest(initial high stop, q)[i]   (resistance line)
- Long stop[i]  = Lowest(initial low stop, q)[i]     (support line)

Signal logic
------------
- Entry (long): close crosses from <= short_stop to > short_stop (price
  breaks above BOTH CKS lines -- short_stop >= long_stop by construction).
- Exit: close crosses back below long_stop (support broken), OR after
  max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept params as keyword args.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def _chande_kroll_stop(df: pd.DataFrame, p: int, atr_mult: float, q: int):
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    atr = _atr(df, p)

    initial_high_stop = high.rolling(p, min_periods=p).max() - atr_mult * atr
    initial_low_stop = low.rolling(p, min_periods=p).min() + atr_mult * atr

    short_stop = initial_high_stop.rolling(q, min_periods=q).max()
    long_stop = initial_low_stop.rolling(q, min_periods=q).min()
    return long_stop, short_stop


def generate_signals(
    price_df: pd.DataFrame,
    p: int = 10,
    atr_mult: float = 1.0,
    q: int = 9,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"].astype(float)

    long_stop, short_stop = _chande_kroll_stop(df, p, atr_mult, q)

    above_short = close > short_stop
    below_long = close < long_stop

    prev_above_short = above_short.shift(1)
    entry = above_short.fillna(False) & ~prev_above_short.fillna(False)
    exit_signal = below_long.fillna(False)

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
    close = df["close"].astype(float)
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

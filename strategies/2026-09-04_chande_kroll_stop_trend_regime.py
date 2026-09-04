"""Strategy: Chande Kroll Stop trend-regime filter with own trailing exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-149):
The Chande Kroll Stop (Tushar Chande & Stanley Kroll) plots a pair of
volatility-adjusted trailing-stop lines: preliminary stop_long =
highest_high(p) - x*ATR(p), preliminary stop_short = lowest_low(p) +
x*ATR(p), then each is smoothed by taking the most protective value over
the last q bars (final Stop Long = highest of preliminary stop_long over q
bars; final Stop Short = lowest of preliminary stop_short over q bars).
Per LuxAlgo's explainer, price trading above BOTH lines defines an uptrend
regime where longs are favored, with Stop Long itself serving as the
trailing exit level (close crossing under Stop Long = long exit). This
strategy operationalizes that directly: long entry when close crosses
above both Stop Long and Stop Short (regime confirmation, entering the
uptrend zone); exit when close crosses back below Stop Long (the
indicator's own designed exit signal) or a max_hold_days time-stop. First
Chande Kroll Stop strategy in this repo -- distinct from Chandelier Exit
(already tested, single-pass ATR offset from one price extreme) since
Chande Kroll adds a second q-bar smoothing pass over the preliminary stop,
and distinct from other ATR-trailing-stop variants already tested.

Signal logic
------------
- ATR = Average True Range(p)
- prelim_stop_long = rolling_max(high, p) - x * ATR
- prelim_stop_short = rolling_min(low, p) + x * ATR
- stop_long = rolling_max(prelim_stop_long, q)
- stop_short = rolling_min(prelim_stop_short, q)
- Entry (long): close crosses above BOTH stop_long and stop_short
  (confirms uptrend regime per the source's own trading guide).
- Exit: close crosses below stop_long (the indicator's designed trailing
  exit), OR max_hold_days elapsed.
- Flat otherwise.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _chande_kroll(df: pd.DataFrame, p: int, x: float, q: int) -> tuple[pd.Series, pd.Series]:
    atr = _atr(df, p)
    prelim_long = df["high"].rolling(p).max() - x * atr
    prelim_short = df["low"].rolling(p).min() + x * atr
    stop_long = prelim_long.rolling(q).max()
    stop_short = prelim_short.rolling(q).min()
    return stop_long, stop_short


def generate_signals(
    price_df: pd.DataFrame,
    p: int = 10,
    x: float = 1.0,
    q: int = 9,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    stop_long, stop_short = _chande_kroll(df, p, x, q)

    entry_cross = (close > stop_long) & (close > stop_short) & (
        (close.shift(1) <= stop_long.shift(1)) | (close.shift(1) <= stop_short.shift(1))
    )
    exit_cross = (close < stop_long) & (close.shift(1) >= stop_long.shift(1))

    entry_arr = entry_cross.fillna(False).to_numpy()
    exit_arr = exit_cross.fillna(True).to_numpy()

    pos_arr = [0] * len(df)
    in_pos = False
    hold_days = 0
    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            if exit_arr[i] or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    p: int = 10,
    x: float = 1.0,
    q: int = 9,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        p=p,
        x=x,
        q=q,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

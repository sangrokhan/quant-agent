"""Strategy: Three Black Crows candlestick pattern as a contrarian mean-reversion entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-001):
The classic "Three Black Crows" bearish reversal candlestick pattern (three
consecutive long bearish candles, each opening within the prior candle's
real body, each closing lower than the prior close, small wicks -- per
quantstrategy.io's mechanical description of the pattern) typically marks a
strong, possibly overextended, short-term selling burst. Rather than trade
it in its traditional direction (as a short-signal after an uptrend, which
this repo's SAFETY.md disallows anyway since it would require shorting),
we test the CONTRARIAN framing: a genuine 3-black-crows completion within
an established uptrend (close > SMA200) represents short-term overselling
/ panic that tends to mean-revert, so we go long at the close of the third
crow and exit on a bounce back above the pattern's own high or a max hold.

This is distinct from the already-rejected Heikin-Ashi N-red-candle
contrarian strategy (2026-09-05-051), which used smoothed Heikin-Ashi
candles and a looser "N consecutive red" rule with no body-containment /
wick-shape criteria; here we use RAW OHLC candles and the stricter,
literature-documented Three Black Crows shape rule (per
https://quantstrategy.io/blog/understanding-the-three-black-crows-candlestick-pattern-for-successful-trading/).

Signal logic
------------
- Uptrend filter: close > SMA(trend_window) (source's own precondition:
  "should only be taken into account when it develops in an established
  uptrend").
- Pattern detection over 3 consecutive daily bars (i-2, i-1, i):
    * All three candles bearish (close < open).
    * Each candle's body length >= min_body_ratio * ATR(atr_window) (avoid
      counting tiny noise candles as "long bearish candles").
    * Each candle's open lies within the real body of the prior candle
      (open_t <= open_{t-1} and open_t >= close_{t-1}), i.e. it opens
      "inside" not with a large gap-down (source: "opens beneath the
      opening of the earlier day ... within the earlier day's body").
    * Each candle closes strictly lower than the prior candle's close
      (monotonic new short-term lows).
    * Lower-wick fraction of each candle's range <= max_wick_ratio (source:
      "bottom wicks of the candles are very little or absent").
- Entry (long): at the close of bar i once the pattern completes AND the
  uptrend filter (measured at bar i-2, i.e. before the selloff began) was
  true.
- Exit: close crosses back above the pattern's high (max(high) over the
  3-bar pattern window, i.e. "recovers what the crows took"), OR after
  max_hold_days trading days, whichever comes first.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    atr_window: int = 14,
    min_body_ratio: float = 0.5,
    max_wick_ratio: float = 0.3,
    max_hold_days: int = 8,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    sma_trend = c.rolling(trend_window).mean()
    atr = _atr(df, atr_window)

    body = (c - o).abs()
    rng = (h - l).replace(0.0, pd.NA)
    lower_wick = (pd.concat([o, c], axis=1).min(axis=1) - l)
    wick_ratio = (lower_wick / rng).astype(float)

    bearish = c < o
    long_body = body >= (min_body_ratio * atr)
    small_wick = wick_ratio <= max_wick_ratio

    n = len(df)
    pattern_complete = pd.Series(False, index=df.index)
    pattern_high = pd.Series(index=df.index, dtype=float)

    o_arr, c_arr = o.values, c.values
    bearish_arr = bearish.values
    long_body_arr = long_body.fillna(False).values
    small_wick_arr = small_wick.fillna(False).values
    h_arr = h.values

    for i in range(2, n):
        idxs = [i - 2, i - 1, i]
        if not all(bearish_arr[j] and long_body_arr[j] and small_wick_arr[j] for j in idxs):
            continue
        ok = True
        for j in (i - 1, i):
            prev = j - 1
            # open within prior candle's real body, and monotonic lower close
            body_lo = min(o_arr[prev], c_arr[prev])
            body_hi = max(o_arr[prev], c_arr[prev])
            if not (body_lo <= o_arr[j] <= body_hi):
                ok = False
                break
            if not (c_arr[j] < c_arr[prev]):
                ok = False
                break
        if not ok:
            continue
        pattern_complete.iloc[i] = True
        pattern_high.iloc[i] = max(h_arr[i - 2], h_arr[i - 1], h_arr[i])

    uptrend_at_start = (c.shift(2) > sma_trend.shift(2)).fillna(False)
    entry = pattern_complete & uptrend_at_start

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    target_high = None
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if c.iloc[i] > target_high or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                target_high = pattern_high.iloc[i]
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret

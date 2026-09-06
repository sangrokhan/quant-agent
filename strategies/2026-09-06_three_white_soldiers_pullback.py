"""Strategy: Three White Soldiers bullish reversal candlestick pattern.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-132):
Per a Google AI-overview synthesis (corroborated by ThinkMarkets and
ChartMill descriptions) of the classic "Three White Soldiers" candlestick
pattern: after a preceding downtrend, three consecutive long-bodied
bullish candles, each opening within the real body of the previous candle
(a "staircase" open) and each closing at or near its high (small/absent
upper wicks), signals a shift from sellers to buyers. ChartMill's own
backtest notes suggest entering on a minor pullback after the third candle
rather than chasing the close, with a stop below the low of the first
candle. This is a genuinely new pattern-recognition family in this repo
(a specific 3-bar OHLC geometric candlestick pattern, distinct from all
previously-tested single-bar patterns like Bullish Engulfing, Hammer-style
Heikin-Ashi reversals, or NR7 breakout bars).

Signal logic
------------
- Preceding downtrend: close 5 bars before the pattern's first candle is
  above the close at the pattern's first candle (i.e. price has been
  falling into the pattern), via `trend_lookback`.
- Three long bullish candles (t-2, t-1, t): each close > open (bullish),
  each body size (close-open) >= long_body_mult * that bar's own
  `body_lookback`-day average |close-open| (a "long body" proxy).
- Staircase opens: open[t-1] within [open[t-2], close[t-2]] and open[t]
  within [open[t-1], close[t-1]].
- Strong closes: each candle's close position within its own range
  ((close-low)/(high-low)) >= strong_close_pct, i.e. closes near the
  high with small upper wicks.
- Entry: on the bar immediately AFTER the pattern completes (bar t+1,
  avoiding lookahead), enter long at that bar's close if that bar's low
  pulls back to within pullback_pct of candle t's close (per ChartMill's
  "enter on a minor pullback after the third candle" note) -- otherwise
  skip this occurrence (no chase entry).
- Exit: max_hold_days time-stop, or a stop-loss at the low of the pattern's
  first candle (t-2), whichever comes first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series {0,1} long/flat
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    trend_lookback: int = 5,
    body_lookback: int = 20,
    long_body_mult: float = 1.2,
    strong_close_pct: float = 0.8,
    pullback_pct: float = 0.02,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    body = (c - o)
    abs_body = body.abs()
    avg_body = abs_body.rolling(body_lookback, min_periods=body_lookback).mean()

    bullish = c > o
    long_body = abs_body >= (long_body_mult * avg_body)
    close_pos = (c - l) / (h - l).replace(0, pd.NA)
    strong_close = close_pos >= strong_close_pct

    good_candle = bullish & long_body & strong_close

    staircase_1 = (o >= o.shift(1)) & (o <= c.shift(1))  # open[t-1..t] within prior body
    downtrend = c.shift(2) < c.shift(2 + trend_lookback)

    # Pattern completes at bar t: candles at t-2, t-1, t are all "good",
    # staircase opens hold for (t-1 vs t-2) and (t vs t-1), preceded by a downtrend.
    pattern_at_t = (
        good_candle
        & good_candle.shift(1).fillna(False)
        & good_candle.shift(2).fillna(False)
        & staircase_1.fillna(False)
        & staircase_1.shift(1).fillna(False)
        & downtrend.fillna(False)
    )

    first_candle_low = l.shift(2)  # low of the pattern's first candle, aligned to bar t
    third_candle_close = c  # candle t's close

    pos = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = None
    stop_price = None

    idx = df.index
    n = len(idx)
    for i in range(n):
        if in_pos:
            days_held = i - entry_idx
            hit_stop = c.iloc[i] <= stop_price if stop_price is not None else False
            hit_time = days_held >= max_hold_days
            if hit_stop or hit_time:
                in_pos = False
                pos.iloc[i] = 0
            else:
                pos.iloc[i] = 1
        else:
            # Check: did the pattern complete at bar i-1? If so, does bar i
            # pull back close enough to third_candle_close to qualify entry?
            if i >= 1 and bool(pattern_at_t.iloc[i - 1]):
                ref_close = third_candle_close.iloc[i - 1]
                if pd.notna(ref_close) and ref_close != 0:
                    pulled_back = l.iloc[i] <= ref_close * (1 + pullback_pct)
                    if pulled_back:
                        in_pos = True
                        entry_idx = i
                        stop_price = first_candle_low.iloc[i - 1]
                        pos.iloc[i] = 1
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    trend_lookback: int = 5,
    body_lookback: int = 20,
    long_body_mult: float = 1.2,
    strong_close_pct: float = 0.8,
    pullback_pct: float = 0.02,
    max_hold_days: int = 10,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        trend_lookback=trend_lookback,
        body_lookback=body_lookback,
        long_body_mult=long_body_mult,
        strong_close_pct=strong_close_pct,
        pullback_pct=pullback_pct,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret

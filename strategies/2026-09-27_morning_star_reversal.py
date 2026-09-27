"""Strategy: Morning Star 3-candle bullish reversal, R-multiple exit.

Hypothesis (source: https://fundedfast.com/learn/candlestick-patterns/morning-star,
read 2026-09-27; citing Bulkowski's Encyclopedia of Candlestick Charts, 2008):
The Morning Star is a 3-candle bullish reversal pattern -- candle 1 is a
large bearish candle, candle 2 has a small body (indecision/compression),
and candle 3 is a bullish candle that closes materially back into candle
1's body. Bulkowski's large-sample study found this pattern acts as a
bullish reversal 78% of the time (rank 12th of 103 patterns tested), though
it's a relatively infrequent pattern (rank 66/103 for frequency). Source's
disclosed trade construction: enter at the close of candle 3 (aggressive
variant used here, vs. the conservative "wait for a break above the pattern
high" variant); stop below the pattern low (min of candle 1 and candle 2
lows); profit target as a fixed R-multiple (source suggests 1.5R-2R) of the
initial risk (entry - stop).

First Morning Star / 3-candle reversal pattern strategy in this repo (0
prior hits for "morning_star"/"evening_star" in strategies_index.jsonl) --
distinct from every other single/double-candle pattern (engulfing, hammer,
key reversal, three-outside-down, etc.) already tried, because this is a
3-candle sequence pattern with an explicit body-overlap confirmation rule
rather than a single-bar shape or 2-bar pattern.

Signal logic
------------
- Candle 1 (2 bars back): bearish (close < open), body size >= body_mult *
  20-bar average true range (a "visibly larger" bearish candle per source).
- Candle 2 (1 bar back): small body, abs(close - open) <= small_body_frac *
  candle 1's body size (indecision/compression).
- Candle 3 (current bar): bullish (close > open), closes at or above the
  midpoint of candle 1's body (source's "closes materially into candle 1's
  body" reclaim rule, parameterized by reclaim_frac of candle 1's body from
  its low).
- Entry: long on the close of candle 3 when all three conditions hold.
- Exit: profit target at entry + reward_r_multiple * (entry - stop_price),
  where stop_price = min(low of candle 1, low of candle 2); OR the stop
  itself is hit intraday-equivalent (next bar's low <= stop_price, using
  close-based approximation since only daily OHLC is available); OR a
  max_hold_days time-stop (this repo's convention for open-ended holds).

Interface contract (see validation/validators.py and validation/grid_test.py):
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


def _true_range(df: pd.DataFrame) -> pd.Series:
    prior_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prior_close).abs(),
            (df["low"] - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def generate_signals(
    price_df: pd.DataFrame,
    body_mult: float = 1.0,
    small_body_frac: float = 0.5,
    reclaim_frac: float = 0.5,
    reward_r_multiple: float = 2.0,
    max_hold_days: int = 15,
    atr_window: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    atr = _true_range(df).rolling(atr_window).mean()

    body1 = (o.shift(2) - c.shift(2))  # candle1 bearish body size (positive if bearish)
    is_bearish1 = c.shift(2) < o.shift(2)
    large_body1 = body1 >= (body_mult * atr.shift(2))

    body2 = (c.shift(1) - o.shift(1)).abs()
    small_body2 = body2 <= (small_body_frac * body1.clip(lower=1e-9))

    is_bullish3 = c > o
    candle1_low = l.shift(2)
    candle1_high = o.shift(2)  # bearish candle: open is near the top
    reclaim_level = candle1_low + reclaim_frac * (candle1_high - candle1_low)
    reclaims3 = c >= reclaim_level

    entry = is_bearish1 & large_body1 & small_body2 & is_bullish3 & reclaims3
    entry = entry.fillna(False)

    stop_price = pd.concat([candle1_low, l.shift(1)], axis=1).min(axis=1)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = 0.0
    stop = 0.0
    target = 0.0
    for i in range(len(df)):
        if in_position:
            held = i - entry_idx
            hit_stop = bool(l.iloc[i] <= stop) if not pd.isna(l.iloc[i]) else False
            hit_target = bool(h.iloc[i] >= target) if not pd.isna(h.iloc[i]) else False
            if hit_stop or hit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                sp = stop_price.iloc[i]
                ep = c.iloc[i]
                if pd.isna(sp) or pd.isna(ep) or ep <= sp:
                    position.iloc[i] = 0
                    continue
                risk = ep - sp
                in_position = True
                entry_idx = i
                entry_price = ep
                stop = sp
                target = ep + reward_r_multiple * risk
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

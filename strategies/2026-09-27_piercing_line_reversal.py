"""Strategy: Piercing Line 2-candle bullish reversal, stop-below-low exit.

Hypothesis (source: https://quantstrategy.io/blog/how-to-interpret-the-piercing-line-candlestick-pattern-for-profitable-trades/,
read 2026-09-27):
The Piercing Line is a 2-candle bullish reversal pattern that forms at the
end of a downtrend: day 1 is a bearish candle, day 2 opens with a gap DOWN
below day 1's close, then reverses to close ABOVE THE MIDPOINT of day 1's
bearish body (piercing back into it, but not fully -- a full close above
day 1's open would instead be a Bullish Engulfing, already tested
separately in this repo). Source's disclosed trade construction: aggressive
entry at the close of the piercing (day 2) candle, or at the open of the
NEXT candle; stop placed just below the low of the piercing candle. No
fixed profit target disclosed -- source suggests R-multiple, prior
support/resistance, or a trailing exit. This repo uses an R-multiple target
(consistent with the recently-tested Morning Star strategy's approach) plus
a time-stop.

First Piercing Line strategy in this repo (0 prior hits for "piercing_line"
in strategies_index.jsonl) -- distinct from the already-tested Bullish
Engulfing (full close above day 1 open) and Dark Cloud Cover (bearish
mirror) because Piercing Line's defining rule is a PARTIAL body reclaim
(close above midpoint, NOT above the full prior open) combined with a
requirement that day 2 open with a gap down.

Signal logic
------------
- Day 1 (prior bar): bearish (close < open), with a "real" body (body size
  >= body_mult * ATR, avoiding tiny-body days).
- Day 2 (current bar): opens with a gap down (open < day1's close);
  is bullish (close > open); closes above the midpoint of day 1's body
  (open1 + close1) / 2, but BELOW day 1's open (to keep this distinct from
  a full engulfing -- reclaim_frac controls how much of day 1's body must be
  reclaimed, capped just under 1.0).
- Entry: long on the close of day 2 (aggressive variant, matching source's
  first option).
- Stop: min(day1_low, day2_low) (source's "below the low of the piercing
  candlestick", widened to also cover day 1's low for safety).
- Target: entry + reward_r_multiple * (entry - stop).
- max_hold_days time-stop as a repo-convention safety net.

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
    body_mult: float = 0.75,
    reclaim_frac_min: float = 0.5,
    reclaim_frac_max: float = 0.95,
    reward_r_multiple: float = 2.0,
    max_hold_days: int = 12,
    atr_window: int = 14,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    atr = _true_range(df).rolling(atr_window).mean()

    o1, c1, l1 = o.shift(1), c.shift(1), l.shift(1)
    day1_bearish = c1 < o1
    body1 = o1 - c1
    real_body1 = body1 >= (body_mult * atr.shift(1))

    gap_down = o < c1
    day2_bullish = c > o
    midpoint1 = (o1 + c1) / 2.0
    reclaim_level_min = c1 + reclaim_frac_min * body1
    reclaim_level_max = c1 + reclaim_frac_max * body1
    closes_above_mid = c >= midpoint1
    not_full_engulf = c <= reclaim_level_max

    entry = (
        day1_bearish
        & real_body1
        & gap_down
        & day2_bullish
        & closes_above_mid
        & not_full_engulf
    ).fillna(False)

    stop_price = pd.concat([l1, l], axis=1).min(axis=1)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
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

"""Strategy: Deliberation (Stalled) candlestick pattern — bearish reversal short entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-010):
Per ForexBee's disclosed rule
(https://forexbee.co/deliberation-candlestick-pattern/): a 3-candle bearish
reversal pattern forming at the top of an uptrend -- bar1 is a tall
bullish candle, bar2 opens above bar1's open and closes above bar1's
high (continuing strength), bar3 has a materially smaller body than bar1
(a "stalling" bar signalling buyers losing momentum) while still closing
bullish (open<close). The shrinking third candle after two strong bullish
candles signals fading buying pressure and a probable short-term reversal.
Distinct from the already-tested Advance Block (a separate 3-candle
stalling pattern with its own shape) and Three White Soldiers. First test
of the Deliberation-specific pattern in this repo (0 prior KB hits).

Signal logic
------------
- bar1: bullish (close>open), body1 = close1-open1.
- bar2: open2 > open1, close2 > high1, bullish (close2>open2).
- bar3: bullish (close3>open3), but body3 < shrink_ratio * body1 (a
  materially smaller body than bar1 -- the "stalling"/deliberation
  signature).
- Short entry at bar3's close on pattern confirmation.
- Exit (cover): close crosses back above bar3's high (pattern
  invalidated), OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (position: -1 short
        / 0 flat, consistent with this repo's other bearish-pattern short
        strategies)
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


def generate_signals(
    price_df: pd.DataFrame,
    shrink_ratio: float = 0.5,
    max_hold_days: int = 8,
) -> pd.Series:
    df = _prep(price_df)
    o, h, c = df["open"], df["high"], df["close"]

    open1, close1 = o.shift(2), c.shift(2)
    open2, close2, high1 = o.shift(1), c.shift(1), h.shift(2)
    open3, close3, high2 = o, c, h.shift(1)

    body1 = (close1 - open1)
    body3 = (close3 - open3)

    bar1_bull = close1 > open1
    bar2_bull = (close2 > open2) & (open2 > open1) & (close2 > high1)
    bar3_bull = close3 > open3
    bar3_small = body3 < (shrink_ratio * body1)

    pattern_confirmed = (bar1_bull & bar2_bull & bar3_bull & bar3_small & (body1 > 0)).fillna(False)
    pattern_high = h  # bar3's own high, used as the invalidation level

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = -1
    entry_high = None
    for i in range(len(df)):
        if not in_pos:
            if bool(pattern_confirmed.iloc[i]):
                in_pos = True
                entry_idx = i
                entry_high = pattern_high.iloc[i]
                position.iloc[i] = -1
            else:
                position.iloc[i] = 0
        else:
            held = i - entry_idx
            invalidated = c.iloc[i] > entry_high if entry_high is not None else False
            if invalidated or held >= max_hold_days:
                position.iloc[i] = 0
                in_pos = False
            else:
                position.iloc[i] = -1

    return position.reindex(df.index).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    shrink_ratio: float = 0.5,
    max_hold_days: int = 8,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    position = generate_signals(price_df, shrink_ratio=shrink_ratio, max_hold_days=max_hold_days)
    # short position: profit when price falls (position=-1 multiplies -daily_ret)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

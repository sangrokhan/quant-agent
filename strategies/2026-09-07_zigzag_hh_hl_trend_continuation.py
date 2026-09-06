"""Strategy: ZigZag pivot Higher-High/Higher-Low trend-continuation entry
with structural swing-low stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-028):
Source: https://www.thinkmarkets.com/en/trading-academy/indicators-and-patterns/zigzag-indicator/
(accessed 2026-09-07). First ZigZag-indicator strategy in this repo.

The ZigZag indicator filters price into a sequence of confirmed swing
highs/lows using a minimum percentage-deviation threshold (the source
recommends 5-8% for swing trading), discarding noise below that
threshold. The source's own framing: "The ZigZag reveals a clear market
structure by showing higher highs and higher lows in uptrends... Notably,
when a new ZigZag pivot forms, it signals that the price has reversed by
the specified percentage threshold, which can be used as a trend
confirmation signal" and "pivot points act as breakout zones in trend
continuations" while also serving as natural stop-loss levels ("set
stop-loss... below swing lows for long trades").

This strategy operationalizes that directly: track ZigZag pivots via a
percentage-deviation threshold; when a NEW confirmed pivot HIGH exceeds
the PRIOR confirmed pivot high, AND the most recent confirmed pivot LOW
is itself higher than the pivot low before it (i.e. the classic Dow-theory
higher-high + higher-low uptrend-confirmation structure, expressed through
ZigZag's own noise-filtered pivots rather than raw local extrema), enter
long. Exit when price closes below the last confirmed swing low (the
source's own suggested structural stop) or after max_hold_days.

ZigZag pivot detection (standard swing-based algorithm, not itself a novel
addition -- implements the deviation-threshold formula described by the
source: a new opposite-direction pivot is confirmed once price reverses by
>= deviation_pct from the running extreme since the last confirmed pivot):
    - Track a running extreme (highest high since last pivot low, or
      lowest low since last pivot high) and its direction.
    - When price reverses away from that running extreme by more than
      deviation_pct, confirm a pivot at the running extreme and flip
      direction.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _zigzag_pivots(df: pd.DataFrame, deviation_pct: float = 5.0):
    """Return two aligned arrays: pivot_high[i] and pivot_low[i], each the
    most recently CONFIRMED pivot high/low value known as of bar i (using
    only information available up to and including bar i -- no lookahead).
    Also returns prev_pivot_high[i]/prev_pivot_low[i] (the pivot before
    the most recent one), and a boolean 'new_pivot_confirmed_here'.
    """
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n = len(df)

    last_pivot_high = np.full(n, np.nan)
    last_pivot_low = np.full(n, np.nan)
    prev_pivot_high = np.full(n, np.nan)
    prev_pivot_low = np.full(n, np.nan)
    new_pivot_up = np.zeros(n, dtype=bool)  # a new pivot HIGH confirmed at this bar
    new_pivot_down = np.zeros(n, dtype=bool)  # a new pivot LOW confirmed at this bar

    if n == 0:
        return last_pivot_high, last_pivot_low, prev_pivot_high, prev_pivot_low, new_pivot_up, new_pivot_down

    direction = 0  # 1 = looking for a high (running up), -1 = looking for a low (running down)
    extreme_price = high[0]
    extreme_idx = 0
    ph = np.nan
    pl = np.nan
    pph = np.nan
    ppl = np.nan
    direction = 1  # start by tracking an emerging high

    for i in range(n):
        if direction == 1:
            if high[i] > extreme_price:
                extreme_price = high[i]
                extreme_idx = i
            elif low[i] <= extreme_price * (1 - deviation_pct / 100.0):
                # confirm a pivot high at extreme_idx
                pph = ph
                ph = extreme_price
                new_pivot_up[i] = True
                direction = -1
                extreme_price = low[i]
                extreme_idx = i
        else:
            if low[i] < extreme_price:
                extreme_price = low[i]
                extreme_idx = i
            elif high[i] >= extreme_price * (1 + deviation_pct / 100.0):
                ppl = pl
                pl = extreme_price
                new_pivot_down[i] = True
                direction = 1
                extreme_price = high[i]
                extreme_idx = i

        last_pivot_high[i] = ph
        last_pivot_low[i] = pl
        prev_pivot_high[i] = pph
        prev_pivot_low[i] = ppl

    return last_pivot_high, last_pivot_low, prev_pivot_high, prev_pivot_low, new_pivot_up, new_pivot_down


def generate_signals(
    price_df: pd.DataFrame,
    deviation_pct: float = 5.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"].to_numpy()
    n = len(df)

    last_ph, last_pl, prev_ph, prev_pl, new_up, new_down = _zigzag_pivots(df, deviation_pct=deviation_pct)

    pos = np.zeros(n, dtype=int)
    in_pos = False
    hold = 0
    stop_level = -np.inf

    for i in range(n):
        # HH + HL uptrend confirmation: a new pivot high just confirmed,
        # exceeding the prior pivot high, AND the most recent pivot low
        # exceeds the pivot low before it.
        uptrend_confirmed = (
            new_up[i]
            and not np.isnan(last_ph[i]) and not np.isnan(prev_ph[i])
            and last_ph[i] > prev_ph[i]
            and not np.isnan(last_pl[i]) and not np.isnan(prev_pl[i])
            and last_pl[i] > prev_pl[i]
        )

        if in_pos:
            hold += 1
            if close[i] < stop_level or hold >= max_hold_days:
                in_pos = False
                hold = 0
                pos[i] = 0
            else:
                pos[i] = 1
        else:
            if uptrend_confirmed:
                in_pos = True
                hold = 0
                stop_level = last_pl[i]
                pos[i] = 1
            else:
                pos[i] = 0

    return pd.Series(pos, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    deviation_pct: float = 5.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns (no transaction costs applied)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change()

    position = generate_signals(price_df, deviation_pct=deviation_pct, max_hold_days=max_hold_days)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)

"""Strategy: ZigZag pivot higher-high breakout trend continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-089),
sourced from https://www.thinkmarkets.com/en/indicators-and-patterns/zigzag-indicator/
(ThinkMarkets, "ZigZag Indicator Signals, Strategies and Integration").
The ZigZag indicator plots swing-high/swing-low pivots whenever price
reverses by more than a set percentage deviation threshold from the last
pivot (filtering out "market noise" moves below that threshold). The
source's own description of "Zig-Zag Indicator Trend Continuation":
    "The ZigZag reveals a clear market structure by showing higher highs
    and higher lows in uptrends... when a new ZigZag pivot forms, it
    signals that the price has reversed by the specified percentage
    threshold, which can be used as a trend confirmation signal at early
    turning points... the pivot points act as breakout zones in trend
    continuations."

Operationalized here as a purely mechanical rule: track ZigZag pivots
with a `deviation_pct` threshold; go long when a newly-confirmed pivot
HIGH exceeds the previous confirmed pivot high (a "higher high" -- the
breakout/trend-continuation signal the source describes), and exit when a
newly-confirmed pivot LOW breaks below the previous confirmed pivot low
(structure broken -- lower low, per the source's own logic that
higher-highs/higher-lows define the uptrend and its breakdown marks the
end of that structure). This is the first ZigZag-based strategy in this
repo -- structurally distinct from every other pivot/breakout strategy
tested (Donchian channel breakout uses a fixed rolling N-day high/low
window, not percentage-deviation-filtered swing pivots; Parabolic SAR/
Chandelier trail on ATR, not price-reversal-magnitude).

Signal logic
------------
- ZigZag pivot detection: walk forward through `close`, tracking the
  running extreme (max since last confirmed low pivot while in an
  "up" leg, min since last confirmed high pivot while in a "down" leg).
  A pivot confirms and the leg direction flips when price retraces by
  >= `deviation_pct` from that running extreme.
- Maintain the last TWO confirmed pivot highs and lows.
- Long entry: a new pivot HIGH confirms that is greater than the
  previous confirmed pivot high (higher-high breakout).
- Exit: a new pivot LOW confirms that is lower than the previous
  confirmed pivot low (lower-low breakdown), or after `max_hold_days`
  (repo-standard safety time-stop).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _zigzag_events(close: pd.Series, deviation_pct: float) -> tuple[list, list]:
    """Returns (higher_high_confirmed_idx, lower_low_confirmed_idx) --
    integer positions where a new pivot high > previous pivot high
    confirms, and where a new pivot low < previous pivot low confirms."""
    values = close.values
    n = len(values)

    higher_high_idx: list[int] = []
    lower_low_idx: list[int] = []

    if n < 3:
        return higher_high_idx, lower_low_idx

    # Initialize: find first meaningful move to establish direction.
    anchor_idx = 0
    anchor_val = values[0]
    direction = 0  # 0 = undetermined, 1 = up leg, -1 = down leg

    prev_pivot_high = None
    prev_pivot_low = None

    for i in range(1, n):
        v = values[i]
        if direction == 0:
            change = (v - anchor_val) / anchor_val if anchor_val else 0.0
            if change >= deviation_pct:
                direction = 1
                anchor_val = v
                anchor_idx = i
            elif change <= -deviation_pct:
                direction = -1
                anchor_val = v
                anchor_idx = i
            continue

        if direction == 1:
            if v > anchor_val:
                anchor_val = v
                anchor_idx = i
            else:
                retrace = (anchor_val - v) / anchor_val if anchor_val else 0.0
                if retrace >= deviation_pct:
                    # Confirm pivot HIGH at anchor_idx.
                    pivot_high_val = anchor_val
                    if prev_pivot_high is not None and pivot_high_val > prev_pivot_high:
                        higher_high_idx.append(anchor_idx)
                    prev_pivot_high = pivot_high_val
                    direction = -1
                    anchor_val = v
                    anchor_idx = i
        else:  # direction == -1
            if v < anchor_val:
                anchor_val = v
                anchor_idx = i
            else:
                retrace = (v - anchor_val) / anchor_val if anchor_val else 0.0
                if retrace >= deviation_pct:
                    # Confirm pivot LOW at anchor_idx.
                    pivot_low_val = anchor_val
                    if prev_pivot_low is not None and pivot_low_val < prev_pivot_low:
                        lower_low_idx.append(anchor_idx)
                    prev_pivot_low = pivot_low_val
                    direction = 1
                    anchor_val = v
                    anchor_idx = i

    return higher_high_idx, lower_low_idx


def generate_signals(
    price_df: pd.DataFrame,
    deviation_pct: float = 0.05,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    higher_high_idx, lower_low_idx = _zigzag_events(close, deviation_pct)
    hh_set = set(higher_high_idx)
    ll_set = set(lower_low_idx)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0

    for i in range(n):
        if in_position:
            hold_count += 1
            if i in ll_set or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if i in hh_set:
                in_position = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

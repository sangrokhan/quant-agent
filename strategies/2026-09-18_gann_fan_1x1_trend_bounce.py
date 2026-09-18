"""Strategy: Gann Fan 1x1-line trend filter with angle-touch bounce entries.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per QuantifiedStrategies.com's Gann Fan Trading Strategy article
(https://www.quantifiedstrategies.com/gann-fan-trading-strategy/), the
source's own disclosed trading rules are: (1) identify a swing pivot (high
or low) as the fan's origin, (2) draw the "1x1 line" at 45 degrees from that
pivot as the primary trend-strength reference, (3) "if price is above the
1x1 line, look for buy signals at intersections of the Gann angles and
price" (trend-following rule), (4) also use the fan's angled lines as
dynamic support/resistance for reversal entries at key levels.

Gann's original 45-degree "1 price unit per 1 time unit" convention is
scale-dependent (meaningless across differently-priced securities without
a fixed price/time unit convention), so -- as is standard practice when
adapting Gann angles programmatically -- we scale the "1x1" slope by the
instrument's own recent ATR per bar, making the fan's angle proportional to
recent volatility rather than a hardcoded price delta. This preserves the
source's own qualitative rule ("steeper angle = stronger trend, 1x1 is the
key line") while making it computable identically on any asset/scale.

Signal logic
------------
- Swing pivot: rolling max(high) over `pivot_lookback` bars -> pivot_price,
  anchored at the bar index where that max occurred (the fan's origin).
- 1x1 line value at each subsequent bar t: pivot_price - atr_per_bar *
  (t - pivot_bar_index), where atr_per_bar = ATR(atr_window) measured AT
  the pivot bar (the "unit of price move per unit of time" fixed at the
  pivot, per Gann convention of anchoring the fan's scale to the origin).
  This produces a downward-sloping 1x1 line from a swing HIGH (the
  reference line price is expected to fall over time in a genuine
  downtrend, in the source's own convention); price closing back ABOVE
  this decaying line signals trend-strength reassertion (bullish, per the
  source's "trend-following" rule: price above 1x1 = buy-signal regime).
- Entry (long): close crosses above the 1x1 line value (source's own
  "price above 1x1 line -> buy signal" rule), confirmed by close above the
  pivot's own low (bounce confirmation, avoids buying deep in an
  unconfirmed decay).
- Exit: close crosses back below the 1x1 line, OR a max_hold_days
  time-stop.
- A new pivot (origin) is established whenever the rolling max(high) makes
  a new high over the lookback window, re-anchoring the fan.

Sources read this iteration:
- https://www.quantifiedstrategies.com/gann-fan-trading-strategy/ (Gann Fan
  construction, 1x1/2:1/3:1/etc angle definitions, and the source's own
  disclosed "price above 1x1 line -> buy signal at Gann-angle
  intersections" trend-following rule).

First Gann Fan / Gann angle strategy in this repo (zero prior matches for
"gann angle"/"gann_fan"/"1x1 line" in strategies_index.jsonl; existing Gann
HiLo Activator entries are an unrelated separate Krausz indicator).

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


def generate_signals(
    price_df: pd.DataFrame,
    pivot_lookback: int = 40,
    atr_window: int = 14,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    atr = _atr(df, atr_window)

    rolling_high = high.rolling(pivot_lookback).max()
    is_new_pivot = high >= rolling_high

    n = len(df.index)
    pivot_price = pd.Series(index=df.index, dtype=float)
    pivot_low = pd.Series(index=df.index, dtype=float)
    pivot_atr = pd.Series(index=df.index, dtype=float)
    pivot_bar_idx = pd.Series(index=df.index, dtype=float)

    last_pivot_price = None
    last_pivot_low = None
    last_pivot_atr = None
    last_pivot_idx = None

    for i in range(n):
        if bool(is_new_pivot.iloc[i]) and not pd.isna(atr.iloc[i]):
            last_pivot_price = float(high.iloc[i])
            last_pivot_low = float(low.iloc[i])
            last_pivot_atr = float(atr.iloc[i]) if atr.iloc[i] > 0 else None
            last_pivot_idx = i
        pivot_price.iloc[i] = last_pivot_price if last_pivot_price is not None else float("nan")
        pivot_low.iloc[i] = last_pivot_low if last_pivot_low is not None else float("nan")
        pivot_atr.iloc[i] = last_pivot_atr if last_pivot_atr is not None else float("nan")
        pivot_bar_idx.iloc[i] = last_pivot_idx if last_pivot_idx is not None else float("nan")

    bar_positions = pd.Series(range(n), index=df.index, dtype=float)
    bars_since_pivot = bar_positions - pivot_bar_idx
    one_by_one_line = pivot_price - pivot_atr * bars_since_pivot

    valid = pivot_price.notna() & pivot_atr.notna() & one_by_one_line.notna()
    above_line = (close > one_by_one_line) & valid
    above_line_prev = above_line.shift(1).fillna(False)
    entry_cross = above_line & (~above_line_prev)
    entry_confirm = entry_cross & (close > pivot_low)
    exit_cross = (~above_line) & above_line_prev

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0
    for i in range(n):
        if not in_position:
            if bool(entry_confirm.iloc[i]):
                in_position = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
        else:
            hold_count += 1
            if bool(exit_cross.iloc[i]) or hold_count >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    pivot_lookback: int = 40,
    atr_window: int = 14,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        pivot_lookback=pivot_lookback,
        atr_window=atr_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

"""Strategy: Turtle Trading System (1 or 2) with true 4-UNIT PYRAMID position
sizing, per the original Dennis/Eckhardt rules as described in
https://www.mql5.com/en/articles/23448 ("The Original Turtle Trading Rules").

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
This repo already has non-pyramiding Turtle System 1 (2026-09-06-125,
accepted QQQ) and System 2 (2026-09-07-014, accepted QQQ) implementations
that take a single all-or-nothing unit at breakout and hold until an
opposite-extreme exit or a flat 2N ATR stop. The ORIGINAL Turtle rules
(per the MQL5 source, corroborating multiple other Turtle-rules writeups)
instead scale INTO winners: after the initial unit, up to 3 additional
units are added each time price moves +1N further in the trade's favor
(N = 20-day ATR at the time of that add), each carrying its own 2N trailing
stop from ITS OWN entry price -- so total exposure ramps from 1x to up to 4x
as a trend extends, with the stop on each unit only ever tightening (never
loosening) as more units stack. This is a genuinely different exposure
profile from the flat single-unit versions already tested: it should do
BETTER on strong sustained trends (letting winners run harder) but WORSE
(deeper drawdowns) if trends frequently reverse right after the first
pyramid add, since more capital is committed exactly when the position was
already working. First continuous multi-unit pyramid-sizing Turtle variant
in this repo (distinct from the flat single-unit System 1/2 already tested,
and from this repo's various unrelated *_sizing_sma_trend.py continuous-
sizing dials, which scale by indicator distance, not by realized-in-trade
favorable excursion).

Signal logic (long-only, per SAFETY.md -- no short leg)
------------
- N = ATR(atr_window), Wilder-style mean of True Range (same construction
  as the existing Turtle System 1/2 strategies in this repo).
- Entry: close makes a new `entry_window`-day high (System 1 default 20,
  System 2 default 55, selectable via `entry_window`) -- opens unit #1 at
  base_unit_size exposure, records that unit's entry price and its own
  stop = entry_price - stop_atr_mult * N(at entry).
- Pyramid adds: while in a position and total units < max_units, if close
  >= (most-recent unit's entry price + add_interval_n * N at the time of
  that most recent unit), add one more unit (+base_unit_size exposure, up to
  leverage_cap), with its own stop = new entry price - stop_atr_mult * N (at
  add time). Each existing unit's own stop is left untouched (per the
  source: "keeps a 2N stop from the most recent entry" -- ratchets tighter
  as later units' stops sit above earlier ones, never loosens).
- Exit (full flatten, all units): close makes a new `exit_window`-day low
  (opposite-extreme exit, same as existing System 1/2), OR close drops to
  or below ANY currently-open unit's own stop (the highest/tightest active
  stop effectively governs), OR a `max_hold_days` time-stop from the
  original (unit #1) entry.
- Exposure returned by generate_signals is CONTINUOUS in [0, leverage_cap]
  (num_open_units * base_unit_size, capped), not a flat 0/1, to actually
  express the pyramid's ramping exposure -- consistent with this repo's
  established continuous-sizing-dial convention (see e.g.
  2026-09-16_ag_selling_exhaustion_fade_sma_trend.py).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def generate_signals(
    price_df: pd.DataFrame,
    entry_window: int = 20,
    exit_window: int = 10,
    atr_window: int = 20,
    stop_atr_mult: float = 2.0,
    add_interval_n: float = 1.0,
    base_unit_size: float = 0.25,
    max_units: int = 4,
    leverage_cap: float = 1.0,
    max_hold_days: int = 90,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    n_atr = _true_range(df).rolling(atr_window).mean()

    entry_high = high.rolling(entry_window).max().shift(1)
    exit_low = low.rolling(exit_window).min().shift(1)
    entry_signal = close > entry_high

    exposure = pd.Series(0.0, index=close.index)

    in_position = False
    units = []  # list of dicts: {"entry_price": float, "stop": float}
    orig_entry_idx = 0

    for i in range(len(close)):
        c = close.iloc[i]
        if in_position:
            held = i - orig_entry_idx
            el = exit_low.iloc[i]
            hit_low_exit = bool(el is not None and not pd.isna(el) and c < el)
            active_stops = [u["stop"] for u in units]
            hit_stop = bool(active_stops) and c <= max(active_stops)
            hit_time = held >= max_hold_days

            if hit_low_exit or hit_stop or hit_time:
                in_position = False
                units = []
                exposure.iloc[i] = 0.0
                continue

            # Pyramid add: price extended add_interval_n * N beyond the
            # most recent unit's own entry price.
            nn = n_atr.iloc[i]
            if len(units) < max_units and not pd.isna(nn) and nn > 0:
                last_entry = units[-1]["entry_price"]
                if c >= last_entry + add_interval_n * nn:
                    new_stop = c - stop_atr_mult * nn
                    units.append({"entry_price": c, "stop": new_stop})

            exposure.iloc[i] = min(len(units) * base_unit_size, leverage_cap)
        else:
            can_enter = bool(entry_signal.iloc[i])
            nn = n_atr.iloc[i]
            if can_enter and not pd.isna(nn) and nn > 0:
                in_position = True
                orig_entry_idx = i
                units = [{"entry_price": c, "stop": c - stop_atr_mult * nn}]
                exposure.iloc[i] = min(len(units) * base_unit_size, leverage_cap)

    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    entry_window: int = 20,
    exit_window: int = 10,
    atr_window: int = 20,
    stop_atr_mult: float = 2.0,
    add_interval_n: float = 1.0,
    base_unit_size: float = 0.25,
    max_units: int = 4,
    leverage_cap: float = 1.0,
    max_hold_days: int = 90,
) -> pd.Series:
    df = _prep(price_df)
    exposure = generate_signals(
        df,
        entry_window=entry_window,
        exit_window=exit_window,
        atr_window=atr_window,
        stop_atr_mult=stop_atr_mult,
        add_interval_n=add_interval_n,
        base_unit_size=base_unit_size,
        max_units=max_units,
        leverage_cap=leverage_cap,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * exposure.shift(1).fillna(0.0)
    return strat_ret

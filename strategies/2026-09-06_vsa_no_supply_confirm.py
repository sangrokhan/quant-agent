"""Strategy: Volume Spread Analysis (VSA) "No Supply" bar + confirmation entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-130):
Per VSA (Wyckoff-derived, sources: quantum-algo.com VSA guide and
tradernewbie.com "No Demand and No Supply Signals in VSA"), a "No Supply"
bar -- a narrow-spread down bar with volume lower than the prior two bars,
occurring after an extended decline / near a local low -- signals that
selling pressure has dried up (professionals no longer hitting bids). The
signal is a warning, not a standalone entry: the source explicitly says to
wait for a confirmation bar (an up bar closing in the top part of its
range) before entering, with a stop below the signal bar's low. This is a
volume-behavior / effort-vs-result strategy, a genuinely new indicator
family in this repo (VSA/Wyckoff bar-by-bar volume analysis), distinct from
existing volume indicators (OBV, CMF, MFI, A/D Line, Force Index, etc.)
which are all *computed* volume oscillators rather than raw bar-context
pattern rules.

Signal logic
------------
- Decline context: close is below its value `decline_lookback` bars ago
  (a simple "we are coming off a decline" filter), matching the source's
  "after an extended decline / near support" confluence requirement.
- No Supply bar (day t): down bar (close < open) OR (close < prior close);
  narrow spread: (high-low) <= narrow_spread_mult * rolling mean spread
  over `spread_window` bars; volume < min(volume[t-1], volume[t-2])
  (lower than the prior two bars, per source definition).
- Confirmation bar (day t+1, checked with a 1-day lag so no lookahead):
  up bar (close > open) AND close position within its own range
  ((close-low)/(high-low)) >= confirm_close_pct (source: "closing on its
  high").
- Entry: long at the close of the confirmation bar.
- Exit: the earlier of (a) max_hold_days time-stop, (b) an opposing "No
  Demand" bar appears while in a position (up bar, narrow spread, volume
  lower than prior two bars -- the mirror-image distribution warning from
  the same source), or (c) a hard stop-loss at stop_atr_mult * ATR(14)
  below the entry price (source: "stop beyond the signal bar's extreme" --
  approximated here with an ATR-based stop for a systematic, symbol-
  independent sizing).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series {0,1} long/flat
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


def _atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window, min_periods=window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    decline_lookback: int = 10,
    spread_window: int = 10,
    narrow_spread_mult: float = 0.75,
    confirm_close_pct: float = 0.6,
    max_hold_days: int = 8,
    stop_atr_mult: float = 2.0,
    atr_window: int = 14,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    spread = (h - l)
    spread_ma = spread.rolling(spread_window, min_periods=spread_window).mean()
    narrow = spread <= (narrow_spread_mult * spread_ma)

    vol_lower_than_prior2 = (v < v.shift(1)) & (v < v.shift(2))

    down_bar = (c < o) | (c < c.shift(1))
    up_bar = (c > o) & (c > c.shift(1))

    decline_context = c < c.shift(decline_lookback)

    no_supply = down_bar & narrow & vol_lower_than_prior2 & decline_context
    no_demand = up_bar & narrow & vol_lower_than_prior2  # distribution warning (any context)

    close_pos = (c - l) / (h - l).replace(0, np.nan)
    confirm_bar = up_bar & (close_pos >= confirm_close_pct)

    # Confirmation must occur the bar *after* a No Supply signal.
    entry_signal = confirm_bar & no_supply.shift(1).fillna(False)

    signal_low = l.where(no_supply).shift(1)  # signal bar's low, aligned to confirm bar
    atr = _atr(df, atr_window)

    pos = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = None
    entry_price = None
    stop_price = None

    idx = df.index
    for i in range(len(idx)):
        ts = idx[i]
        if in_pos:
            days_held = i - entry_idx
            hit_stop = c.iloc[i] <= stop_price if stop_price is not None else False
            hit_time = days_held >= max_hold_days
            hit_no_demand = bool(no_demand.iloc[i])
            if hit_stop or hit_time or hit_no_demand:
                in_pos = False
                pos.iloc[i] = 0
            else:
                pos.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_pos = True
                entry_idx = i
                entry_price = c.iloc[i]
                a = atr.iloc[i]
                stop_price = entry_price - stop_atr_mult * a if pd.notna(a) else None
                pos.iloc[i] = 1
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    decline_lookback: int = 10,
    spread_window: int = 10,
    narrow_spread_mult: float = 0.75,
    confirm_close_pct: float = 0.6,
    max_hold_days: int = 8,
    stop_atr_mult: float = 2.0,
    atr_window: int = 14,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        decline_lookback=decline_lookback,
        spread_window=spread_window,
        narrow_spread_mult=narrow_spread_mult,
        confirm_close_pct=confirm_close_pct,
        max_hold_days=max_hold_days,
        stop_atr_mult=stop_atr_mult,
        atr_window=atr_window,
    )
    daily_ret = close.pct_change().fillna(0.0)
    # Position at t determines exposure to return realized from t to t+1.
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret

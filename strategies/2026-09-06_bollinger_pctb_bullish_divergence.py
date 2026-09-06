"""Strategy: Bollinger %B bullish divergence (price lower low, %B higher low).

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per a Google AI-overview synthesis of Ultra Blue Forex / The Trading Pit
%B-divergence explainers (this iteration's search), Bollinger %B
divergence identifies weakening downside momentum distinct from a plain
%B threshold read: "Bullish (Positive) Divergence Setup: price makes a
lower low; %B makes a higher low (failing to drop as deeply below zero or
matching prior oversold extremes) ... Entry Rule: Go long when a
confirmation trigger happens, such as %B crossing back upward." This is
the first %B-DIVERGENCE strategy in this repo -- distinct from every
plain %B threshold/mean-reversion variant already tested (2026-09-04-107
single-day %B<0 mean-reversion, 2026-09-05-011 %B+MFI dual-thrust,
2026-09-06-092 Larry Connors 3-day %B<0.2 rule, 2026-09-06-119 Vervoort
zero-lag-rainbow %B), none of which compare price's own swing structure
against %B's swing structure -- here the entry signal is a genuine
divergence (price makes a new low while the oscillator doesn't confirm
it), the same class of signal already validated as a useful technique
elsewhere in this repo for other oscillators (e.g. MFI divergence
2026-09-05-061, RVI divergence 2026-09-05-057), but never yet tried with
%B specifically.

Signal logic
------------
- %B(bb_window, bb_std) = (close - lower_band) / (upper_band - lower_band),
  the standard normalized Bollinger position (0 = at lower band, 1 = at
  upper band).
- Divergence detection: over a rolling `swing_lookback`-bar window, if
  today's close is a new `swing_lookback`-bar low (close == rolling min)
  while %B is HIGHER than the %B value recorded at the previous
  `swing_lookback`-bar low within the same lookback (bullish divergence:
  price weaker, oscillator stronger), flag a divergence.
- Entry (long): a divergence was flagged within the last
  `confirm_window` bars AND %B crosses back above `confirm_level`
  (default 0.2, the source's "%B crossing back upward" confirmation
  trigger).
- Exit: %B crosses back below `confirm_level` after being above it, %B
  reaches `exit_level` (default 0.8, overbought), or a `max_hold_days`
  time-stop.
- Long-only, flat otherwise.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def _percent_b(close: pd.Series, bb_window: int, bb_std: float) -> pd.Series:
    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    upper = sma + bb_std * std
    lower = sma - bb_std * std
    band_width = (upper - lower).replace(0, np.nan)
    pct_b = (close - lower) / band_width
    return pct_b


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    swing_lookback: int = 10,
    confirm_window: int = 5,
    confirm_level: float = 0.2,
    exit_level: float = 0.8,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    pct_b = _percent_b(close, bb_window, bb_std)

    rolling_min = close.rolling(swing_lookback).min()
    is_swing_low = close == rolling_min

    # For each swing-low bar, compare its %B to the previous swing-low's %B.
    divergence = pd.Series(False, index=close.index)
    last_swing_low_pctb = None
    last_swing_low_price = None
    for i in range(n):
        if bool(is_swing_low.iloc[i]) and pd.notna(pct_b.iloc[i]):
            cur_price = close.iloc[i]
            cur_pctb = pct_b.iloc[i]
            if last_swing_low_price is not None and cur_price < last_swing_low_price and cur_pctb > last_swing_low_pctb:
                divergence.iloc[i] = True
            last_swing_low_price = cur_price
            last_swing_low_pctb = cur_pctb

    divergence_recent = divergence.rolling(confirm_window).max().astype(bool)
    pct_b_prev = pct_b.shift(1)
    confirm_cross = (pct_b > confirm_level) & (pct_b_prev <= confirm_level)
    entry_trigger = divergence_recent.shift(1).fillna(False) & confirm_cross.fillna(False)

    exit_cross = (pct_b < confirm_level) & (pct_b_prev >= confirm_level)
    exit_overbought = pct_b >= exit_level

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            ec = bool(exit_cross.iloc[i]) if pd.notna(exit_cross.iloc[i]) else False
            eo = bool(exit_overbought.iloc[i]) if pd.notna(exit_overbought.iloc[i]) else False
            if ec or eo or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entered = bool(entry_trigger.iloc[i]) if pd.notna(entry_trigger.iloc[i]) else False
            if entered:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    swing_lookback: int = 10,
    confirm_window: int = 5,
    confirm_level: float = 0.2,
    exit_level: float = 0.8,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        bb_window=bb_window,
        bb_std=bb_std,
        swing_lookback=swing_lookback,
        confirm_window=confirm_window,
        confirm_level=confirm_level,
        exit_level=exit_level,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

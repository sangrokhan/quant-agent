"""Strategy: Fair Value Gap (FVG) retracement-fill mean reversion, daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-018):
Per ICT/"smart money concepts" methodology (journali.io/strategies/ict-fvg,
backed by the source's own disclosed backtest: raw FVG fill rate ~78%,
trading only fills that align with higher-timeframe bias ~65% WR), a 3-bar
"fair value gap" -- an imbalance where bar1's high sits below bar3's low
(bullish) or bar1's low sits above bar3's high (bearish) -- tends to get
revisited ("filled") before price continues. This repo operationalizes the
3-candle ICT concept directly on DAILY bars (source's own examples are on
intraday ES/NQ; we deliberately test the daily-bar analog, distinct from any
other gap-based strategy already in this repo, e.g. the overnight
open-vs-prior-close gap-fade strategies 2026-09-03-010/2026-09-08-016 which
are a completely different mechanical definition of "gap").

Signal logic
------------
- Detect a bullish 3-bar FVG at bar i (using bars i-2, i-1, i): a gap exists
  when low[i] > high[i-2] (i.e. bar i-1 displaced hard up, leaving unfilled
  space between bar i-2's high and bar i's low). Gap zone = [high[i-2],
  low[i]].
- Higher-timeframe bias filter: only take the bullish gap if close[i] is
  above its `trend_sma_window`-day SMA (uptrend context), matching the
  source's explicit "require the higher-timeframe bias to support the
  direction of the FVG" entry rule.
- Entry (long): on a later bar j > i, price retraces back down INTO the gap
  zone (low[j] <= gap_top) while the gap is still "fresh" (unfilled/untested,
  within `max_gap_age_days` bars of formation, and not already breached
  below gap_bottom -- a clean pass-through invalidates the setup per the
  source's own invalidation rule).
- Exit: first target = opposite end of the gap (gap_top, the "fill"), OR a
  hard stop just beyond the far edge (gap_bottom - stop_atr_mult*ATR) per the
  source's stop rule, OR a `max_hold_days` time-stop if neither triggers.
- Flat whenever not in an active long. Long-only (bearish FVGs not traded,
  to keep this a direct daily-bar test of the source's bullish-continuation
  setup without doubling the parameter surface).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_window: int = 50,
    max_gap_age_days: int = 10,
    stop_atr_mult: float = 1.5,
    atr_window: int = 14,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    n = len(df)

    sma = close.rolling(trend_sma_window).mean()
    atr = _atr(df, atr_window)

    # Detect bullish 3-bar FVGs: at index i, gap exists if low[i] > high[i-2].
    gap_exists = pd.Series(False, index=df.index)
    gap_top = pd.Series(index=df.index, dtype=float)
    gap_bottom = pd.Series(index=df.index, dtype=float)
    for i in range(2, n):
        if low.iloc[i] > high.iloc[i - 2]:
            gap_exists.iloc[i] = True
            gap_top.iloc[i] = low.iloc[i]
            gap_bottom.iloc[i] = high.iloc[i - 2]

    position = pd.Series(0, index=df.index, dtype=int)

    in_position = False
    entry_idx = 0
    active_gap_top = None
    active_gap_bottom = None
    active_stop = None

    # Track most recent unfilled/untested fresh bullish gap eligible for entry.
    pending_gap_idx = None
    pending_gap_top = None
    pending_gap_bottom = None

    for i in range(n):
        if in_position:
            held = i - entry_idx
            hit_target = high.iloc[i] >= active_gap_top
            hit_stop = low.iloc[i] <= active_stop
            if hit_target or hit_stop or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                active_gap_top = active_gap_bottom = active_stop = None
                continue
            position.iloc[i] = 1
            continue

        # Register a new fresh gap this bar (only trend-aligned ones considered).
        if gap_exists.iloc[i] and not pd.isna(sma.iloc[i]) and close.iloc[i] > sma.iloc[i]:
            pending_gap_idx = i
            pending_gap_top = gap_top.iloc[i]
            pending_gap_bottom = gap_bottom.iloc[i]

        # Check whether we have a live pending gap to trade against.
        if pending_gap_idx is not None:
            age = i - pending_gap_idx
            if age > max_gap_age_days or age <= 0:
                if age > max_gap_age_days:
                    pending_gap_idx = None
                position.iloc[i] = 0
                continue
            # Invalidate if price already traded cleanly through (closed below bottom).
            if close.iloc[i] < pending_gap_bottom:
                pending_gap_idx = None
                position.iloc[i] = 0
                continue
            # Entry trigger: price retraces down INTO the gap zone.
            if low.iloc[i] <= pending_gap_top and not pd.isna(atr.iloc[i]):
                in_position = True
                entry_idx = i
                active_gap_top = pending_gap_top
                active_gap_bottom = pending_gap_bottom
                active_stop = pending_gap_bottom - stop_atr_mult * atr.iloc[i]
                pending_gap_idx = None
                position.iloc[i] = 1
                continue

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

"""Strategy: Standalone Chandelier Exit trend-flip breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-064):
Per Quantum Algo's Chandelier Exit guide (browser_exec fallback -- web_search
DDGS errored with a TLS connection error), the Chandelier Exit is an
ATR-based trailing stop line: long_stop = Highest(High, period) -
ATR(period)*multiplier, ratcheting UP only (never decreasing) while price
stays above it. This strategy tests the STANDALONE trend-flip use: rather
than using the Chandelier line merely as a trailing-stop FILTER for a
separate entry signal (already tested in this repo as 2026-09-04-035,
Chandelier+StochRSI dip-buy, rejected), treat a close crossing back ABOVE
the Chandelier long_stop line (after having been below it, i.e. a fresh
regime flip from downtrend to uptrend) as the entry TRIGGER itself. This is
the genuinely different mechanic: Chandelier-as-trigger rather than
Chandelier-as-filter.

Signal logic
------------
- long_stop_raw[t] = Highest(High, period)[t] - multiplier*ATR(period)[t]
- long_stop[t] = long_stop_raw[t] if close[t] > long_stop[t-1] else
  max(long_stop_raw[t], long_stop[t-1]) (standard Chandelier ratchet: only
  moves up while in an uptrend, resets down when price closes below it).
- Entry (long): close crosses above long_stop (close[t] > long_stop[t] AND
  close[t-1] <= long_stop[t-1]) -- fresh trend-flip trigger.
- Exit: close crosses back below long_stop (the indicator's own designed
  exit), or a max_hold_days time-stop.
- Flat (no position) whenever not in an active long.

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5/6):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _chandelier_long_stop(df: pd.DataFrame, period: int, multiplier: float) -> pd.Series:
    highest_high = df["high"].rolling(period).max()
    atr = _atr(df, period)
    raw_stop = highest_high - multiplier * atr

    close = df["close"].to_numpy()
    raw = raw_stop.to_numpy()
    n = len(df)
    stop = np.full(n, np.nan)

    for i in range(n):
        if np.isnan(raw[i]):
            continue
        if i == 0 or np.isnan(stop[i - 1]):
            stop[i] = raw[i]
            continue
        if close[i - 1] > stop[i - 1]:
            stop[i] = max(raw[i], stop[i - 1])
        else:
            stop[i] = raw[i]

    return pd.Series(stop, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 22,
    multiplier: float = 3.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    long_stop = _chandelier_long_stop(df, period=period, multiplier=multiplier)
    close = df["close"]

    above = close > long_stop
    cross_up = above & (~above.shift(1).fillna(False))
    cross_down = (~above) & above.shift(1).fillna(False)

    cross_up_arr = cross_up.to_numpy()
    cross_down_arr = cross_down.to_numpy()
    pos_arr = np.zeros(len(df), dtype=int)

    in_pos = False
    entry_idx = -1
    for i in range(len(df)):
        if in_pos:
            held = i - entry_idx
            if cross_down_arr[i] or held >= max_hold_days:
                in_pos = False
            else:
                pos_arr[i] = 1
        if not in_pos and cross_up_arr[i]:
            in_pos = True
            entry_idx = i
            pos_arr[i] = 1

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 22,
    multiplier: float = 3.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        period=period,
        multiplier=multiplier,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change()
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    return strat_returns

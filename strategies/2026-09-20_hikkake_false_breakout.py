"""Strategy: Hikkake Pattern (Chesler false-breakout of an inside bar).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per https://oxfordstrat.com/trading-strategies/hikkake-pattern/ (Dan
Chesler, CTM/CTA; original 42-futures-market backtest 1980-2014): the
Hikkake pattern is a "false breakout of an inside bar" reversal setup.

Setup (using bar indices i-2, i-1, i):
    Inside bar at i-1: High[i-1] < High[i-2] AND Low[i-1] > Low[i-2].
    Bullish Hikkake at i: High[i] < High[i-1] AND Low[i] < Low[i-1]
        (bar i makes a LOWER high and LOWER low than the inside bar --
        i.e. price broke down out of the inside-bar range, but this is
        read as a bear-trap: the false breakdown should reverse up).
    Bearish Hikkake at i: High[i] > High[i-1] AND Low[i] > Low[i-1]
        (mirror -- false breakout to the upside, expected to reverse down).

Entry (per source, adapted from stop orders to next-bar daily execution
since this repo trades close-to-close, not intrabar stops):
    Long: enter next bar if/when price later trades above the inside bar's
    high (buy-stop semantics) -- approximated here as: enter at the next
    day's close if that close is above the inside bar's high, checked for
    up to `signal_window` (default 3, per source) bars after the pattern.
    Short: mirror (sell-stop below inside bar's low).

Exit (source offers three exit types; we implement the two testable within
this repo's daily-bar structure):
    - Time exit: flat after `time_index` days in the trade (source's
      sensitivity test found longer holds, time_index>10, preferred).
    - ATR stop-loss: ATR(atr_length)*atr_stop below/above entry price.
    - (Pattern-exit via lowest-low/highest-high of the setup window is
      approximated by the ATR stop, which serves a similar protective
      role -- omitted as a separate leg to keep the strategy testable
      with only kwarg-based tunable parameters.)

Trend filter (source's own optional, found "redundant" in their
sensitivity test -- we include it as a tunable off-by-default parameter
so the grid can test whether it's redundant on our own equity/crypto data
too): Close[i] >= Close[i-trend_index] for longs (mirror for shorts);
trend_index=0 disables the filter, per source's own convention.

First Hikkake Pattern strategy in this repo (2 prior tag-only hits were a
different reversal concept, not tested) -- distinct from all prior
inside-bar/outside-bar/NR7 strategies via requiring the SPECIFIC two-bar
false-breakout sequence with directional confirmation, not just an inside
bar or a volatility-contraction breakout alone.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({-1, 0, 1})
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if len(df.index) > 1:
        median_gap = pd.Series(df.index).diff().median()
        if pd.notna(median_gap) and median_gap < pd.Timedelta(hours=20):
            df = df.resample("1D").agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            ).dropna()
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
    signal_window: int = 3,
    time_index: int = 15,
    trend_index: int = 0,
    atr_length: int = 20,
    atr_stop: float = 6.0,
) -> pd.Series:
    """Return a {-1, 0, 1} position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    n = len(df)

    atr = _true_range(df).ewm(alpha=1.0 / atr_length, adjust=False, min_periods=atr_length).mean().values

    high_v = high.values
    low_v = low.values
    close_v = close.values

    # Inside bar at i-1 relative to i-2.
    inside_bar = np.zeros(n, dtype=bool)
    inside_bar[2:] = (high_v[1:-1] < high_v[:-2]) & (low_v[1:-1] > low_v[:-2])

    # Bullish/bearish hikkake at i (needs inside bar at i-1).
    bullish_hikkake = np.zeros(n, dtype=bool)
    bearish_hikkake = np.zeros(n, dtype=bool)
    bullish_hikkake[2:] = inside_bar[2:] & (high_v[2:] < high_v[1:-1]) & (low_v[2:] < low_v[1:-1])
    bearish_hikkake[2:] = inside_bar[2:] & (high_v[2:] > high_v[1:-1]) & (low_v[2:] > low_v[1:-1])

    inside_bar_high = np.roll(high_v, 1)  # high of bar i-1 (the inside bar), aligned to pattern bar i
    inside_bar_low = np.roll(low_v, 1)

    position = np.zeros(n, dtype=int)
    entry_price = np.full(n, np.nan)
    entry_idx = -1
    current_pos = 0

    # Track pending long/short setups waiting for a breakout within signal_window.
    pending_long_from = -1
    pending_short_from = -1
    pending_long_ib_high = np.nan
    pending_short_ib_low = np.nan

    for i in range(n):
        if current_pos != 0:
            held = i - entry_idx
            stop_hit = False
            if current_pos == 1:
                stop_level = entry_price[entry_idx] - atr_stop * atr[entry_idx] if not np.isnan(atr[entry_idx]) else -np.inf
                if low_v[i] <= stop_level:
                    stop_hit = True
            else:
                stop_level = entry_price[entry_idx] + atr_stop * atr[entry_idx] if not np.isnan(atr[entry_idx]) else np.inf
                if high_v[i] >= stop_level:
                    stop_hit = True
            if stop_hit or held >= time_index:
                current_pos = 0
                position[i] = 0
                continue
            position[i] = current_pos
            continue

        # Register new pending setups (only when flat).
        if bullish_hikkake[i]:
            pending_long_from = i
            pending_long_ib_high = inside_bar_high[i]
        if bearish_hikkake[i]:
            pending_short_from = i
            pending_short_ib_low = inside_bar_low[i]

        # Check trend filter helper.
        def trend_ok_long(idx):
            if trend_index <= 0 or idx - trend_index < 0:
                return trend_index <= 0
            return close_v[idx] >= close_v[idx - trend_index]

        def trend_ok_short(idx):
            if trend_index <= 0 or idx - trend_index < 0:
                return trend_index <= 0
            return close_v[idx] <= close_v[idx - trend_index]

        entered = False
        # Check pending long: does today's close break above inside-bar high?
        if pending_long_from >= 0 and (i - pending_long_from) <= signal_window and i > pending_long_from:
            if close_v[i] > pending_long_ib_high and trend_ok_long(i):
                current_pos = 1
                entry_idx = i
                entry_price[i] = close_v[i]
                position[i] = 1
                pending_long_from = -1
                entered = True
        if not entered and pending_long_from >= 0 and (i - pending_long_from) > signal_window:
            pending_long_from = -1

        if not entered and pending_short_from >= 0 and (i - pending_short_from) <= signal_window and i > pending_short_from:
            if close_v[i] < pending_short_ib_low and trend_ok_short(i):
                current_pos = -1
                entry_idx = i
                entry_price[i] = close_v[i]
                position[i] = -1
                pending_short_from = -1
                entered = True
        if not entered and pending_short_from >= 0 and (i - pending_short_from) > signal_window:
            pending_short_from = -1

        if not entered:
            position[i] = 0

    return pd.Series(position, index=df.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret

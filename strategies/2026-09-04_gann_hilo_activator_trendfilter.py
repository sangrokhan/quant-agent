"""Strategy: Gann HiLo Activator flip signal, gated by a long-term SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-128):
The Gann HiLo Activator (W.D. Gann concept, popularized by Robert Krausz,
Stocks & Commodities V16:2) is a trailing trend-state line: while in an
"up" state it plots the moving average of the trailing N lows (acting as
support), while in a "down" state it plots the moving average of the
trailing N highs (acting as resistance). The state flips whenever the
close crosses through the opposite-side average, and per
enlightenedstocktrading.com's own worked example, "A rules-based strategy
using the Gann HiLo Activator might involve buying when the indicator
flips from resistance to support and selling when it flips back", with the
recommended risk-mitigation being to combine it with a long-term moving
average trend filter (only take the flip-to-support long signal when price
is above a slower trend-defining SMA) to avoid trading whipsaws in
range-bound/choppy markets. This is the first Gann HiLo Activator strategy
tested in this repo -- distinct from all prior trailing-stop/flip-state
indicators (Chandelier Exit uses ATR bands off a fixed lookback high/low,
Parabolic SAR uses an acceleration factor, SuperTrend uses ATR bands off a
midpoint) since Gann HiLo's stepped line is a pure trailing SMA-of-high or
SMA-of-low that only recomputes off the OPPOSITE side after a state flip.

Signal logic
------------
- period: lookback window (default 10, source-typical default 3-13) for
  the trailing SMA-of-high / SMA-of-low used in each state.
- State starts "down" (uses SMA of highs as resistance) until close first
  closes above it, flipping to "up" (switches to SMA of lows as support).
- Long entry: state flips from down->up (i.e. close crosses above the
  resistance line) AND close is above a trend_window-period SMA (the
  source's recommended long-term trend filter, avoids trading flips in a
  broader downtrend).
- Exit: state flips back down->up->down (close crosses below the new
  support line), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _gann_hilo(df: pd.DataFrame, period: int) -> pd.Series:
    """Return the Gann HiLo Activator line (stepped support/resistance)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    sma_high = high.rolling(period).mean()
    sma_low = low.rolling(period).mean()

    n = len(df)
    line = pd.Series(index=df.index, dtype=float)
    state_up = pd.Series(index=df.index, dtype=object)  # True=up(support), False=down(resistance)

    up = False  # start in "down" state (resistance) until proven otherwise
    for i in range(n):
        if pd.isna(sma_high.iloc[i]) or pd.isna(sma_low.iloc[i]):
            line.iloc[i] = float("nan")
            state_up.iloc[i] = up
            continue
        c = close.iloc[i]
        if up:
            # currently support (sma_low); flip to down if close breaks below it
            if c < sma_low.iloc[i]:
                up = False
        else:
            # currently resistance (sma_high); flip to up if close breaks above it
            if c > sma_high.iloc[i]:
                up = True
        line.iloc[i] = sma_low.iloc[i] if up else sma_high.iloc[i]
        state_up.iloc[i] = up
    return line, state_up


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 10,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    _, state_up = _gann_hilo(df, period)
    state_up_bool = state_up.astype("boolean").fillna(False)
    flip_to_up = state_up_bool & (~state_up_bool.shift(1).fillna(False))
    flip_to_down = (~state_up_bool) & (state_up_bool.shift(1).fillna(False))

    trend_sma = close.rolling(trend_window).mean()
    trend_ok = close > trend_sma

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = bool(flip_to_down.iloc[i])
            if exit_now or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entry_now = bool(flip_to_up.iloc[i]) and bool(trend_ok.iloc[i]) if pd.notna(trend_ok.iloc[i]) else False
            if entry_now:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 10,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, period=period, trend_window=trend_window, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

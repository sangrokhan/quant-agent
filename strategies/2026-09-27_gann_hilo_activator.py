"""Strategy: Gann High-Low (Hi-Lo) Activator, long-only trend-following flip
system with the indicator line itself as the trailing stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-108),
sourced from a Google AI-overview synthesis of Robert Krausz's 1998 Gann
Hi-Lo Activator (TradingPedia / Enlightened Stock Trading / Stocks &
Commodities TASC sources, read via browser_exec this iteration -- DDGS
web_search backend returned no results for this query):

Formula (classic default lookback n=3):
  - Uptrend state: HiLo[t] = SMA(Low, n)[t] (line trails BELOW price, built
    from the low-based SMA).
  - Downtrend state: HiLo[t] = SMA(High, n)[t] (line trails ABOVE price,
    built from the high-based SMA).
  - State transition ("the flip"): if currently in downtrend state (line
    above price) and a bar CLOSES ABOVE the current high-based line, state
    flips to uptrend (line switches below price, now computed from the
    low-based SMA going forward). Symmetric flip downward in the long-only
    adaptation is simply an exit, not a short entry (per repo SAFETY.md,
    long-only).
  - Exact trading rule (source's own): "Enter a long position when the
    price closes above the Gann Hi-Lo line while the line is flipped below
    the price (transition from bearish to bullish state)... Use the active
    Gann Hi-Lo line value itself as a dynamic trailing stop-loss level for
    open positions, updating it on each new bar until a closing breach
    triggers a reversal exit."

This repo has extensive SuperTrend/Chandelier-Exit-style flip-trailing-stop
strategies (71 prior "supertrend"/"chandelier" KB hits), but those are all
ATR-based trailing stops. The Gann Hi-Lo Activator is mechanically distinct:
its trailing stop is a plain SMA of highs/lows (no ATR/volatility scaling at
all), so its band width is driven purely by the recent high-low range over a
short (n=3 classic) lookback rather than a volatility multiplier -- first
Gann Hi-Lo strategy in this repo (0 prior KB hits for "Gann High Low"/"Gann
Hi-Lo"/"Gann Activator").

Signal logic (long-only adaptation)
------------------------------------
- Compute both candidate lines: sma_low = SMA(Low, n), sma_high = SMA(High, n).
- Maintain a state variable (uptrend/downtrend) via the flip rule above,
  starting from a downtrend default until the first flip.
- Long entry: on the bar where state flips from downtrend to uptrend (close
  crosses above the then-active high-based line).
- Exit: on the bar where state flips from uptrend back to downtrend (close
  crosses below the then-active low-based line) -- this IS the trailing
  stop-loss mechanic per the source, not a separate exit rule.
- No time-stop needed (the flip itself is the exit trigger, per source).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
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


def generate_signals(
    price_df: pd.DataFrame,
    n: int = 13,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma_low = low.rolling(n, min_periods=n).mean()
    sma_high = high.rolling(n, min_periods=n).mean()

    close_arr = close.to_numpy()
    sma_low_arr = sma_low.to_numpy()
    sma_high_arr = sma_high.to_numpy()
    n_bars = len(df)

    # state: True = uptrend (line = sma_low, below price), False = downtrend
    # (line = sma_high, above price). Start in downtrend by convention until
    # the first valid bar with both SMAs available.
    state = np.zeros(n_bars, dtype=bool)
    pos_arr = np.zeros(n_bars, dtype=int)

    first_valid = n  # first index where rolling SMA(n) is available
    if first_valid >= n_bars:
        return pd.Series(pos_arr, index=df.index, dtype=int)

    cur_uptrend = False  # start in downtrend state
    for i in range(first_valid, n_bars):
        if np.isnan(sma_low_arr[i]) or np.isnan(sma_high_arr[i]):
            state[i] = cur_uptrend
            continue

        if not cur_uptrend:
            # downtrend state: line = sma_high; check for flip up
            if close_arr[i] > sma_high_arr[i]:
                cur_uptrend = True
        else:
            # uptrend state: line = sma_low; check for flip down
            if close_arr[i] < sma_low_arr[i]:
                cur_uptrend = False

        state[i] = cur_uptrend
        pos_arr[i] = 1 if cur_uptrend else 0

    position = pd.Series(pos_arr, index=df.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    n: int = 13,
) -> pd.Series:
    """Return the strategy's daily return series (position lagged 1 day)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(price_df, n=n)

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

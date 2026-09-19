"""Strategy: SMA-crossover entry with a fixed hold period equal to the SMA window.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-065):
Per QuantifiedStrategies.com's "Simple Moving Average Trading Strategy:
Backtest, Trading Rules And Statistics"
(https://www.quantifiedstrategies.com/simple-moving-average-trading-strategy/),
the source's own disclosed finding: "The highest average gain per trade
was observed when buying after the price crosses above the 200-day SMA
and holding for 200 days" -- returning an average 10.93% per trade. This
is a genuinely distinct construction from every other SMA-crossover
strategy in this repo: rather than exiting on the OPPOSITE crossover
(price falls back below the SMA) or a fixed independent time-stop, the
holding period is set EQUAL TO the SMA's own lookback window (sma_window
== hold_days), i.e. "hold for as long as you looked back to confirm the
trend" -- a specific pairing the source explicitly highlights as
producing its best per-trade result, not an arbitrary combination.

First strategy in this repo using this "hold period tied to the
indicator's own lookback window" construction. Distinct from all prior
SMA-crossover entries (opposite-crossover exit), fixed-hold pullback
strategies (2026-09-10-033, hold_days is an independently-tuned short
horizon unrelated to any indicator window), and N-day-high fixed-horizon
breakouts (2026-09-12-207, hold period tied to the BREAKOUT lookback,
not an SMA).

We treat sma_window as the single tunable grid parameter (hold_days is
mechanically pinned to sma_window per the source's own rule, not
independently tunable, to stay faithful to the hypothesis under test).
Re-entry: once a hold completes, a new signal can only trigger on a
FRESH crossover (close re-crosses above the SMA) -- consecutive days of
close > SMA while already in a position, or immediately after a hold
ends, don't restart the hold; this avoids the position flickering into
back-to-back overlapping holds and stays close to "buy AFTER the
cross", a discrete event.

Signal logic
------------
- sma = SMA(close, sma_window).
- fresh_cross_up = (close > sma) AND (close.shift(1) <= sma.shift(1))
  (bullish crossover event, evaluated once per crossing).
- On a fresh_cross_up day, go long for the following sma_window trading
  days (from that day's close through close of day + sma_window).
- No new entry starts while a hold is already active (a crossover event
  occurring mid-hold is ignored, consistent with the source's discrete
  "buy after the cross" framing rather than pyramiding).
- Long-only; flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(sma_window).mean()

    above = (close > sma).fillna(False)
    fresh_cross_up = above & (~above.shift(1).fillna(False))

    position = pd.Series(0, index=close.index)
    n = len(close)
    idx_positions = {ts: i for i, ts in enumerate(close.index)}
    i = 0
    cross_indices = [idx_positions[ts] for ts in close.index[fresh_cross_up.values]]
    cross_set = set(cross_indices)

    hold_until = -1
    for i in range(n):
        if i <= hold_until:
            position.iloc[i] = 1
            continue
        if i in cross_set:
            hold_until = min(i + sma_window, n - 1)
            position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    sma_window: int = 200,
) -> pd.Series:
    """Return the strategy's daily return series."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(df, sma_window=sma_window)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

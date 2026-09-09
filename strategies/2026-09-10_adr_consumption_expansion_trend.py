"""Strategy: ADR (Average Daily Range) consumption range-expansion trend continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-043):
Per audacity.capital's Average Daily Range guide (visited this iteration,
https://audacity.capital/trading-guides/average-daily-range): "ADR consumed"
(today's high-low range divided by its own trailing average, i.e. how much
of the "typical" daily range has already been used) is a context filter, and
the source's own explicit guidance is that a day consuming well BEYOND
100% of its historical ADR (backed by trend) should NOT be faded -- it
signals genuine range expansion / trend continuation, not exhaustion.

This iteration operationalizes that as a daily-bar swing strategy (source's
own examples are intraday, adapted here to end-of-day signals): on a
bullish trading day (close>open) where the day's own high-low range exceeds
its trailing ADR by a wide margin (adr_consumed_ratio >= expansion_threshold,
e.g. 1.3-1.5x), AND price is above its own SMA(trend_window) (broad uptrend
context, avoiding fighting the wider trend), take a long entry -- betting
the expansion day marks genuine trend continuation rather than treating it
as an overextended level to fade. Exit on trend break (close<SMA) or a
time-stop. This is the first ADR-CONSUMPTION-RATIO (distinct from the
already-tested NR7 contraction-precedes-expansion pattern id=2026-09-04-081,
the DeMark Range Expansion Index id=2026-09-06-167, and the single-bar
Volatility-Ratio breakout id=2026-09-07-019, all of which use different
constructions) strategy tried in this repo.

Signal logic
------------
- daily_range = high - low
- adr = daily_range.rolling(adr_window).mean() (trailing average, excludes
  today via shift(1) to avoid look-ahead: today's own range shouldn't be
  part of its own baseline).
- adr_consumed_ratio = daily_range / adr.shift(1)
- bullish_day = close > open
- trend_up = close > close.rolling(trend_window).mean()
- Entry (long): bullish_day AND adr_consumed_ratio >= expansion_threshold
  AND trend_up, all on the same bar (enter next bar per generate_returns'
  1-day shift).
- Exit: close < close.rolling(trend_window).mean() (trend break) OR
  max_hold_days time-stop.
- Flat otherwise.

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


def generate_signals(
    price_df: pd.DataFrame,
    adr_window: int = 14,
    expansion_threshold: float = 1.3,
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    daily_range = high - low
    adr = daily_range.rolling(adr_window).mean().shift(1)
    adr_consumed_ratio = daily_range / adr

    bullish_day = close > open_
    trend_sma = close.rolling(trend_window).mean()
    trend_up = close > trend_sma

    entry = bullish_day & (adr_consumed_ratio >= expansion_threshold) & trend_up.fillna(False)
    exit_trend_break = ~trend_up.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
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

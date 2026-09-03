"""Strategy: TD Sequential (DeMark) TD-Setup 9-count exhaustion mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-032):
Per the widely-documented Tom DeMark "TD Setup" counting rule (surfaced in
Google search snippets for multiple sources, e.g. discoveryalert.com.au's
sequential-nine-exhaustion article, when the specific detail page 404'd):
a "TD Buy Setup" completes when NINE CONSECUTIVE bars each close LOWER
than the close 4 bars prior (a persistent, un-interrupted downtrend
sequence) -- signaling seller exhaustion and a potential mean-reversion
bounce. Symmetrically, a "TD Sell Setup" completes on nine consecutive
higher-than-4-bars-ago closes, signaling buyer exhaustion. This
strategy operationalizes the long-only bullish exhaustion signal: enter
long when a TD Buy Setup count reaches 9, exit after a fixed holding
period or when price recovers a threshold amount (source's own
described interpretation: TD9 is a WARNING/exhaustion flag rather than a
direct trade trigger -- Sofien Kaabar's Medium piece, surfaced in the
same search, explicitly cautions "many traders use TD9 as an exhaustion
signal rather than a direct buy/sell command"). This is the first
DeMark-family sequential/counting indicator tested in this repo --
distinct construction from every prior strategy (a pure BAR-COUNT
consecutive-comparison rule, not a rolling-window statistic or
moving-average-based calculation).

Signal logic
------------
- TD Buy Setup count: for each bar, count consecutive bars (up to and
  including today) where close < close[4 bars prior]. Resets to 0 the
  first time this condition breaks.
- Entry (long): TD Buy Setup count reaches setup_count (source: 9) for
  the first time (fresh completion, not every bar the count stays >= 9).
- Exit: after max_hold_days bars, OR when close crosses back above the
  SMA(exit_sma_window) (a simple mean-reversion target), whichever comes
  first.
- Flat otherwise; long-only, no shorting (TD Sell Setup / short side not
  implemented, consistent with this repo's long-only convention).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _td_buy_setup_count(close: pd.Series, lookback: int = 4) -> pd.Series:
    condition = close < close.shift(lookback)
    counts = pd.Series(0, index=close.index, dtype=int)
    running = 0
    for i in range(len(close)):
        c = condition.iloc[i]
        if bool(c):
            running += 1
        else:
            running = 0
        counts.iloc[i] = running
    return counts


def generate_signals(
    price_df: pd.DataFrame,
    setup_count: int = 9,
    exit_sma_window: int = 10,
    max_hold_days: int = 8,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    td_count = _td_buy_setup_count(close, lookback=4)
    fresh_completion = (td_count == setup_count) & (td_count.shift(1) < setup_count)
    fresh_completion = fresh_completion.fillna(False)

    sma_exit = close.rolling(exit_sma_window).mean()
    exit_recover = close > sma_exit

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_recover.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(fresh_completion.iloc[i]):
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

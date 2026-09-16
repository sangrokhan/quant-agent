"""Strategy: TD Sequential "Perfected" Buy Setup (Tom DeMark).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-017):
Per https://sai-tai.com/other/econ/indicators-strategies/td-sequential/
(read via browser_exec after web_search backend failures this iteration):
a raw TD Buy Setup (9 consecutive closes each lower than the close 4 bars
prior) was already tested in this repo (2026-09-04-032, rejected, decisive
Sharpe fail full-sample, apparent "best cell" was a high-vol-tercile
artifact) and its Countdown-confirmation variants (2026-09-08-079,
2026-09-09-031) were also rejected/near-miss. This entry tests a DIFFERENT,
not-yet-tried confirmation layer that the source explicitly calls out as
producing a "stronger signal": the Setup is only actionable if it is
"perfected" -- the low of bar 8 or bar 9 of the 9-count must be less than
or equal to the lows of bars 6 and 7. This is a pure intrabar
price-structure filter (not a Countdown/bar-counting extension), designed
to exclude weak/unconfirmed 9-counts where the low hasn't actually made a
fresh low near the end of the sequence -- i.e. select for genuine
exhaustion structure rather than a naive close-only count.

Signal logic
------------
- Buy Setup: 9 consecutive daily closes each below the close 4 bars
  earlier (bar index 0..8 relative to the count start).
- Perfected filter: low[8] <= min(low[6], low[7])  OR  low[7] <= min(low[6], low[5])
  (per source's own rule: "low of bar 8 or 9 is <= lows of bars 6 and 7").
- Entry (long): close of the day the perfected 9-count completes.
- Exit: close crosses back above a short SMA(exit_sma_window), OR the
  count breaks (a close higher than close[4] resets prematurely -- not
  modeled here, simple time-stop instead per repo convention), OR after
  max_hold_days.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _perfected_buy_setup_completions(df: pd.DataFrame, setup_count: int = 9) -> pd.Series:
    """Return a boolean Series, True on the bar where a perfected TD Buy
    Setup completes (setup_count consecutive closes each below close[4]
    bars prior, with the perfection filter on the last two bars' lows)."""
    close = df["close"]
    low = df["low"]
    n = len(df)

    # condition[i] True if close[i] < close[i-4]
    cond = close < close.shift(4)
    cond = cond.fillna(False)

    completes = pd.Series(False, index=df.index)
    run_len = 0
    for i in range(n):
        if cond.iloc[i]:
            run_len += 1
        else:
            run_len = 0
        if run_len >= setup_count:
            # bars of the setup run are i-setup_count+1 .. i (0-indexed
            # within the whole series); map to "bar 6,7,8,9" of the
            # 9-count (1-indexed: bar9 = i, bar8 = i-1, bar7 = i-2, bar6 = i-3)
            if i - 3 < 0:
                continue
            low9 = low.iloc[i]
            low8 = low.iloc[i - 1]
            low7 = low.iloc[i - 2]
            low6 = low.iloc[i - 3]
            perfected = (low9 <= min(low6, low7)) or (low8 <= min(low6, low7))
            if perfected:
                completes.iloc[i] = True
            # only fire once per completed run (reset so overlapping
            # >9-length runs don't fire every subsequent bar)
            run_len = 0
    return completes


def generate_signals(
    price_df: pd.DataFrame,
    setup_count: int = 9,
    exit_sma_window: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    sma_exit = close.rolling(exit_sma_window).mean()

    entries = _perfected_buy_setup_completions(df, setup_count=setup_count)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(len(df)):
        if not in_pos:
            if entries.iloc[i]:
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
        else:
            hold_days = i - entry_idx
            exit_signal = close.iloc[i] > sma_exit.iloc[i]
            time_stop = hold_days >= max_hold_days
            if exit_signal or time_stop:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    setup_count: int = 9,
    exit_sma_window: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        df,
        setup_count=setup_count,
        exit_sma_window=exit_sma_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    # position held during day t earns day t's return (signal computed on
    # close of t-1, enter/hold through t) -- shift by 1 to avoid lookahead
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

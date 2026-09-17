"""Strategy: Short-lookback, shallow-threshold price z-score mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD, this iteration):
Per StatOasis "Z-Score Mean Reversion Strategy: 2,400 Backtests on Futures
and SPY" (Ali Casey, https://statoasis.com/overfit/research/understanding-
z-score-and-its-application-in-mean-reversion-strategies, read this
iteration via browser_exec after web_search DDGS backend returned generic
SEO-blog noise instead of the target article), a systematic 2,400-variant
sweep of z-score mean reversion across ES futures and SPY (2007-2026 / 1993-
2026) found that although NO variant beats buy-and-hold outright, a "stable
region" clusters at a SHORT 10-day lookback with a SHALLOW entry threshold
(z below -1, not the deep -2/-3 extremes), exiting when z snaps back above a
modest +0.5 (not all the way to 0), with median R-expectancy 0.14-0.28
across that stable region on SPY -- and this specific narrow-lookback/
shallow-threshold combination clears the study's own random-permutation
control on SPY (score 0.62 vs 0.114), unlike deeper/longer variants.

This is a DIRECT, source-grounded parameter-regime distinct from the
already-rejected 2026-09-04-082 z-score mean reversion test in this repo
(window=15, entry_z=2.0 deep threshold, exit_z=0.0, best Sharpe only 0.785).
That prior test swept deep/long configs; this iteration specifically tests
the SHORT-lookback (~10d) + SHALLOW-threshold (~1.0 std) region the source's
own large-N sweep flagged as the one statistically-stable pocket, plus the
shallower exit_z=0.5 rather than the full-reversion exit_z=0.0 used before.

Signal logic
------------
- rolling_mean = SMA(close, window), rolling_std = STD(close, window)
- z = (close - rolling_mean) / rolling_std
- Entry (long): fresh cross of z below -entry_z (yesterday z >= -entry_z,
  today z < -entry_z) -- avoids re-entering every day while still extreme.
- Exit: z crosses back above exit_z, OR max_hold_days elapses, whichever
  first (source's own tested time-exits ranged 0-15 days).
- Long-only, flat otherwise, single position at a time.

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


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 10,
    entry_z: float = 1.0,
    exit_z: float = 0.5,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    rolling_mean = close.rolling(window).mean()
    rolling_std = close.rolling(window).std()
    z = (close - rolling_mean) / rolling_std.replace(0, pd.NA)
    z = z.fillna(0.0)

    fresh_entry = (z < -entry_z) & (z.shift(1) >= -entry_z)
    fresh_entry = fresh_entry.fillna(False)

    pos = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(n):
        if in_pos:
            held = i - entry_idx
            if z.iloc[i] >= exit_z or held >= max_hold_days:
                in_pos = False
            else:
                pos.iloc[i] = 1
        if not in_pos and fresh_entry.iloc[i]:
            in_pos = True
            entry_idx = i
            pos.iloc[i] = 1
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    window: int = 10,
    entry_z: float = 1.0,
    exit_z: float = 0.5,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return daily strategy returns (position lagged 1 day to avoid look-ahead)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        window=window,
        entry_z=entry_z,
        exit_z=exit_z,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret

"""Strategy: Pretty Good Oscillator (PGO, Mark Johnson) breakout threshold
crossover with zero-line exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-049):
Per pineify.app's PGO explainer (read in-browser, web_extract failed --
DuckDuckGo search-only backend), Mark Johnson's Pretty Good Oscillator
normalizes the distance between close and its SMA by the ATR-smoothed true
range, giving a cross-asset-comparable "how many average day ranges is
price stretched from its mean" reading. Johnson's own explicit breakout
system rule: PGO crossing above +3.0 signals a strong bullish breakout
(long entry); PGO reverting to the zero line (close returning to its SMA)
is the exit signal. Default length=89 (source: "matches Johnson's original
longer-term breakout use case", best on daily/weekly). First PGO strategy
in this repo -- 0 prior hits on "PGO"/"Pretty Good Oscillator" in
strategies_index.jsonl.

Signal logic
------------
- PGO(n) = (close - SMA(close, n)) / EMA(TrueRange, n)
- Entry (long): PGO crosses above `entry_threshold` (default 3.0).
- Exit: PGO crosses back below `exit_threshold` (default 0.0, the zero
  line per Johnson's own exit rule), OR a max_hold_days time-stop (source
  doesn't specify a stop; added for risk control per repo convention).
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


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _pgo(df: pd.DataFrame, n: int) -> pd.Series:
    close = df["close"]
    sma = close.rolling(n).mean()
    tr = _true_range(df)
    ema_tr = tr.ewm(span=n, adjust=False).mean()
    return (close - sma) / ema_tr.replace(0, pd.NA)


def generate_signals(
    price_df: pd.DataFrame,
    n: int = 89,
    entry_threshold: float = 3.0,
    exit_threshold: float = 0.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    pgo = _pgo(df, n)
    cross_up = (pgo > entry_threshold) & (pgo.shift(1) <= entry_threshold)
    cross_down = (pgo < exit_threshold) & (pgo.shift(1) >= exit_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(len(close)):
        if not in_pos:
            if bool(cross_up.iloc[i]) if pd.notna(cross_up.iloc[i]) else False:
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
        else:
            held = i - entry_idx
            cd = bool(cross_down.iloc[i]) if pd.notna(cross_down.iloc[i]) else False
            if cd or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    n: int = 89,
    entry_threshold: float = 3.0,
    exit_threshold: float = 0.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no txn costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        n=n,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)

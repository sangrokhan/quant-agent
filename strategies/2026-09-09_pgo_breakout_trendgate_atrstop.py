"""Strategy: Pretty Good Oscillator (PGO) breakout, fixed for the
near-miss 2026-09-08-049 via a 200-day SMA uptrend gate on entry (to
address the QQQ MDD breach) and a tighter ATR-based trailing stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-052):
Direct follow-up to this repo's near-miss 2026-09-08-049 (PGO breakout
threshold crossover, entry_threshold=2.0/n=55). That entry's rejection
reason: "Full-sample Sharpe just short of 1.0 threshold on both QQQ
(0.998) and SPY (0.914)...QQQ additionally barely breaches MDD cap
(0.252 vs 0.25)." Both misses were narrow.

This repo's own accumulated finding (e.g. 2026-09-03-021, 2026-09-04-089,
2026-09-07-007, 2026-09-09-049) is that a 200-day SMA uptrend gate on
entry reduces exactly the kind of counter-trend drawdown that pushed
-049's QQQ MDD over its cap. This iteration applies that fix directly:
only take the PGO breakout entry (PGO crosses above entry_threshold) when
close is also above its 200-day SMA, plus tightens the exit with an
ATR-based trailing stop (2x ATR below the highest close since entry) in
addition to the original zero-line-reversion exit, to cap downside on any
trade that reverses hard after entry.

Same PGO formula and breakout-threshold/zero-line-exit mechanics as -049
otherwise, for a clean comparison.

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
    n: int = 55,
    entry_threshold: float = 2.0,
    exit_threshold: float = 0.0,
    max_hold_days: int = 60,
    trend_sma_window: int = 200,
    atr_window: int = 14,
    atr_stop_multiplier: float = 2.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    pgo = _pgo(df, n)
    trend_sma = close.rolling(trend_sma_window).mean()
    uptrend = close > trend_sma

    tr = _true_range(df)
    atr = tr.ewm(span=atr_window, adjust=False).mean()

    cross_up = (pgo > entry_threshold) & (pgo.shift(1) <= entry_threshold)
    cross_down = (pgo < exit_threshold) & (pgo.shift(1) >= exit_threshold)
    entry_cond = cross_up & uptrend.fillna(False)

    close_vals = close.values
    atr_vals = atr.values
    n_bars = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    highest_since_entry = None
    for i in range(n_bars):
        if not in_pos:
            if bool(entry_cond.iloc[i]) if pd.notna(entry_cond.iloc[i]) else False:
                in_pos = True
                entry_idx = i
                highest_since_entry = close_vals[i]
                position.iloc[i] = 1
        else:
            held = i - entry_idx
            highest_since_entry = max(highest_since_entry, close_vals[i])
            trailing_stop = highest_since_entry - atr_stop_multiplier * atr_vals[i]
            cd = bool(cross_down.iloc[i]) if pd.notna(cross_down.iloc[i]) else False
            stop_hit = close_vals[i] < trailing_stop
            if cd or stop_hit or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Return daily strategy returns (position-weighted, no txn costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)

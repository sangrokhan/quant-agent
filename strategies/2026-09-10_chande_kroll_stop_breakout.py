"""Strategy: Chande Kroll Stop (CKSP) dual-line breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per LuxAlgo/TrendSpider CKSP guides (SERP-sourced, corroborated across both
sources), the Chande Kroll Stop is a two-stage ATR-based trailing-stop
indicator: an initial ATR-offset stop off the recent p-period extreme
(high/low), then smoothed by taking the most protective value over a
shorter q-period window. Standard published defaults: p=10, x=1 (ATR
multiplier), q=9. TrendSpider's disclosed entry rule: a buy signal fires
when price crosses above BOTH the long-stop and short-stop lines
(confirming a fresh uptrend breakout beyond the whole stop-band, not just
one line), and a sell/exit signal when price falls below both. First
Chande Kroll Stop strategy in this repo (0 prior entries) -- distinct from
other ATR-based trailing-stop indicators (Chandelier Exit, ATR trailing
stop) via its two-stage extreme-then-smooth construction with two lines
that must both be crossed.

Calculation (per LuxAlgo's stated standard implementation):
    first_high_stop = Highest(high, p) - x * ATR(p)
    first_low_stop  = Lowest(low, p)  + x * ATR(p)
    stop_short = Highest(first_high_stop, q)   # upper line
    stop_long  = Lowest(first_low_stop, q)     # lower line

Signal logic
------------
- Entry (long): close crosses above BOTH stop_long and stop_short (the
  entire CKSP band), per TrendSpider's disclosed dual-line breakout rule.
- Exit: close falls below stop_long (the trailing-stop line for a long
  position, i.e. once price closes back inside/below the CKSP band's
  lower line the original stop-loss purpose of the indicator triggers),
  or a max_hold_days time-stop.
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


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prior_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prior_close).abs(),
            (low - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _cksp(df: pd.DataFrame, p: int, x: float, q: int) -> tuple[pd.Series, pd.Series]:
    high, low = df["high"], df["low"]
    atr = _atr(df, p)

    first_high_stop = high.rolling(p).max() - x * atr
    first_low_stop = low.rolling(p).min() + x * atr

    stop_short = first_high_stop.rolling(q).max()
    stop_long = first_low_stop.rolling(q).min()
    return stop_long, stop_short


def generate_signals(
    price_df: pd.DataFrame,
    p: int = 10,
    x: float = 1.0,
    q: int = 9,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    stop_long, stop_short = _cksp(df, p, x, q)

    entry_signal = (close > stop_long) & (close > stop_short) & (
        (close.shift(1) <= stop_long.shift(1)) | (close.shift(1) <= stop_short.shift(1))
    )
    exit_signal = close < stop_long

    valid = stop_long.notna() & stop_short.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = None

    for i in range(len(df.index)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue

        if in_position:
            held_days = i - entry_idx
            if exit_signal.iloc[i] or held_days >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_signal.iloc[i]:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    p: int = 10,
    x: float = 1.0,
    q: int = 9,
    max_hold_days: int = 30,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(price_df, p=p, x=x, q=q, max_hold_days=max_hold_days)

    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_ret
    strat_returns.name = "strategy_returns"
    return strat_returns

"""Strategy: Chandelier Exit trend-flip, ADX trend-strength gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-065):
Direct follow-up to near-miss 2026-09-09-064 (standalone Chandelier Exit
trend-flip breakout, rejected -- full-sample Sharpe 0.815 on SPY, 0.810 on
QQQ, both close misses vs the 1.0 threshold; grid pass_fraction 0.313 was
the best of this cron trigger with a genuinely broad vol-regime spread,
suggesting the underlying signal has real but insufficiently-filtered
edge). This iteration adds an ADX(14) trend-strength confirmation filter
(only take the Chandelier trend-flip entry when ADX > adx_threshold,
confirming a genuinely strong trend rather than a weak whipsaw-prone
crossing) -- the identical fix pattern used successfully elsewhere in this
repo's history to cut low-conviction trades from a directionally-correct
but noisy trigger. Thesis: filtering out weak-trend Chandelier flips (which
are more likely to whipsaw and drag down the Sharpe) should push the
full-sample Sharpe above 1.0 while preserving the core edge.

Signal logic
------------
- Identical Chandelier long_stop construction and trend-flip entry
  trigger as 2026-09-09-064 (close crosses above the ATR-based ratcheting
  long_stop line), PLUS an entry-only requirement that ADX(14) > adx_threshold
  (confirmed trend strength, standard Wilder ADX construction).
- Exit: close crosses back below the Chandelier long_stop line (unchanged
  from 2026-09-09-064), or a max_hold_days time-stop. No ADX-based exit --
  keeping the exit side simple and testing purely whether the ADX ENTRY
  filter alone recovers the Sharpe.

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5/6):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _chandelier_long_stop(df: pd.DataFrame, period: int, multiplier: float) -> pd.Series:
    highest_high = df["high"].rolling(period).max()
    atr = _atr(df, period)
    raw_stop = highest_high - multiplier * atr

    close = df["close"].to_numpy()
    raw = raw_stop.to_numpy()
    n = len(df)
    stop = np.full(n, np.nan)

    for i in range(n):
        if np.isnan(raw[i]):
            continue
        if i == 0 or np.isnan(stop[i - 1]):
            stop[i] = raw[i]
            continue
        if close[i - 1] > stop[i - 1]:
            stop[i] = max(raw[i], stop[i - 1])
        else:
            stop[i] = raw[i]

    return pd.Series(stop, index=df.index)


def _adx(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    atr = _atr(df, window)
    plus_dm_s = pd.Series(plus_dm, index=df.index).rolling(window).mean()
    minus_dm_s = pd.Series(minus_dm, index=df.index).rolling(window).mean()

    plus_di = 100 * (plus_dm_s / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm_s / atr.replace(0, np.nan))

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.rolling(window).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 22,
    multiplier: float = 2.0,
    adx_threshold: float = 20.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    long_stop = _chandelier_long_stop(df, period=period, multiplier=multiplier)
    close = df["close"]
    adx = _adx(df, window=14)

    above = close > long_stop
    cross_up = above & (~above.shift(1).fillna(False))
    cross_down = (~above) & above.shift(1).fillna(False)

    trend_confirmed = adx > adx_threshold
    entry = cross_up & trend_confirmed.fillna(False)

    entry_arr = entry.to_numpy()
    cross_down_arr = cross_down.to_numpy()
    pos_arr = np.zeros(len(df), dtype=int)

    in_pos = False
    entry_idx = -1
    for i in range(len(df)):
        if in_pos:
            held = i - entry_idx
            if cross_down_arr[i] or held >= max_hold_days:
                in_pos = False
            else:
                pos_arr[i] = 1
        if not in_pos and entry_arr[i]:
            in_pos = True
            entry_idx = i
            pos_arr[i] = 1

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 22,
    multiplier: float = 2.0,
    adx_threshold: float = 20.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        period=period,
        multiplier=multiplier,
        adx_threshold=adx_threshold,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change()
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    return strat_returns

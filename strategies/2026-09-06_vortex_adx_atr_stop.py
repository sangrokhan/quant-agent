"""Strategy: Vortex Indicator (VI+/VI-) crossover with ADX strength filter
and ATR trailing stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-091),
sourced from https://pinescriptforge.com/strategy/vortex-indicator
("Vortex Indicator (VI) trend strategy: long entry when VI+ crosses above
VI- and both > 1.0; short entry when VI- crosses above VI+; exit on
opposing crossover; filter with ADX>20 to avoid whipsaws; stop at 1.5x
ATR.").

This repo already tested a plain Vortex crossover gated by a close>SMA
trend filter (2026-09-04-040, id=2026-09-04-040, accepted QQQ only, SPY
near-miss, crypto rejected). This variant is mechanically distinct in two
ways per the source page:
  1. Uses an ADX(14) > adx_threshold strength filter instead of a simple
     SMA trend filter -- ADX directly measures trend strength/conviction
     rather than just price location relative to a moving average, so it
     should reject more of the choppy/sideways whipsaw entries that hurt
     the earlier SMA-filtered variant (mid/high-vol cells failed there).
  2. Adds an ATR-based trailing stop (atr_mult * ATR(14) below the highest
     close since entry) rather than relying solely on the opposing VI
     crossover to exit -- this should cut losses faster in adverse moves,
     directly targeting the earlier variant's max-drawdown risk in
     higher-vol regimes.
  3. Requires the VI+ value itself to exceed vi_min_level (source's ">1.0"
     magnitude filter) at the crossover bar, screening out low-magnitude
     marginal crossovers.

Signal logic
------------
- Vortex: VI+ = sum(|high[t]-low[t-1]|, n) / sum(TR, n);
          VI- = sum(|low[t]-high[t-1]|, n) / sum(TR, n).
- ADX(14) computed via standard Wilder smoothing of +DI/-DI.
- Long entry: VI+ crosses above VI- AND VI+ > vi_min_level AND
  ADX > adx_threshold (trend-strength confirmation).
- Exit: VI- crosses back above VI+, OR close drops below
  (highest close since entry) - atr_mult * ATR(14) (trailing stop), OR
  max_hold_days time-stop (repo standard safety valve).

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


def _vortex(df: pd.DataFrame, window: int) -> tuple[pd.Series, pd.Series]:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    prev_low = low.shift(1)
    prev_high = high.shift(1)

    vm_plus = (high - prev_low).abs()
    vm_minus = (low - prev_high).abs()
    tr = _true_range(df)

    tr_sum = tr.rolling(window).sum()
    vi_plus = vm_plus.rolling(window).sum() / tr_sum
    vi_minus = vm_minus.rolling(window).sum() / tr_sum
    return vi_plus, vi_minus


def _adx(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)

    tr = _true_range(df)
    atr = tr.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()

    plus_di = 100 * (plus_dm.ewm(alpha=1 / window, adjust=False, min_periods=window).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1 / window, adjust=False, min_periods=window).mean() / atr)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    return adx


def _atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    tr = _true_range(df)
    return tr.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    vortex_window: int = 14,
    adx_threshold: float = 20.0,
    vi_min_level: float = 1.0,
    atr_mult: float = 1.5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    vi_plus, vi_minus = _vortex(df, vortex_window)
    adx = _adx(df, 14)
    atr = _atr(df, 14)

    crossed_up = (vi_plus > vi_minus) & (vi_plus.shift(1) <= vi_minus.shift(1))
    crossed_down = (vi_minus > vi_plus) & (vi_minus.shift(1) <= vi_plus.shift(1))

    entry_ok = crossed_up & (vi_plus > vi_min_level) & (adx > adx_threshold)

    entry_arr = entry_ok.fillna(False).values
    exit_cross_arr = crossed_down.fillna(False).values
    close_arr = close.values
    atr_arr = atr.values

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0
    highest_close = np.nan

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if not np.isnan(close_arr[i]):
                highest_close = max(highest_close, close_arr[i])
            stop_level = highest_close - atr_mult * atr_arr[i] if not np.isnan(atr_arr[i]) else -np.inf
            stopped_out = (not np.isnan(close_arr[i])) and close_arr[i] < stop_level
            if exit_cross_arr[i] or stopped_out or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                highest_close = np.nan
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_arr[i]:
                in_position = True
                hold_count = 0
                highest_close = close_arr[i]
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

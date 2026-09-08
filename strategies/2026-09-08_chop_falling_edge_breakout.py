"""Strategy: Choppiness Index falling-edge regime transition + EMA trend +
Donchian resistance breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-048):
Per trendsandbreakouts.com's Choppiness Index (CHOP, Bill Dreiss) trading
rules (read in-browser, web_search DuckDuckGo backend errored out for the
first query so fell back to browser_exec bing.com search), the source's
explicit "practical workflow": take long breakouts only when (1) price is
above a rising EMA, (2) Choppiness Index is FALLING from a higher zone
(a regime *transition* signal -- the market shifting from range-bound
toward trending -- not just a static "CI below threshold" snapshot), and
(3) price actually breaks a well-defined resistance level (source warns
explicitly against anticipating breakouts from a high CI reading alone;
wait for the structural break). This is a distinct construction from the
already-tested 2026-09-04-059 (accepted QQQ only), which used a static
CI<38 threshold + SMA filter with no falling-edge transition requirement
and no explicit price-structure breakout component -- here the breakout
through an N-day Donchian high is the actual trigger, CI/EMA are gates.

Signal logic
------------
- Choppiness Index: CI(n) = 100 * log10(sum(TR, n) / (HH(n)-LL(n))) / log10(n)
- EMA(ema_window) trend filter: close > EMA (source's "rising EMA" proxy).
- CI falling-edge: CI was >= chop_high_zone within the last `chop_lookback`
  bars, and has since fallen below `chop_high_zone` (transitioning out of
  the choppy/range zone) -- NOT merely "CI currently low".
- Donchian breakout: close crosses above the highest close of the prior
  `donchian_window` bars (resistance breakout, source's explicit
  "well-defined resistance area" trigger).
- Entry (long): all three conditions true simultaneously.
- Exit: close falls back below the EMA (trend filter breaks), OR CI rises
  back above `chop_high_zone` (regime reverts to choppy), OR a
  max_hold_days time-stop.

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


def _choppiness_index(df: pd.DataFrame, n: int) -> pd.Series:
    tr = _true_range(df)
    tr_sum = tr.rolling(n).sum()
    hh = df["high"].rolling(n).max()
    ll = df["low"].rolling(n).min()
    rng = (hh - ll).replace(0, np.nan)
    ratio = (tr_sum / rng).clip(lower=1e-9)
    ci = 100.0 * np.log10(ratio) / np.log10(n)
    return ci


def generate_signals(
    price_df: pd.DataFrame,
    chop_window: int = 14,
    chop_high_zone: float = 61.8,
    chop_lookback: int = 10,
    ema_window: int = 50,
    donchian_window: int = 20,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ci = _choppiness_index(df, chop_window)
    ema = close.ewm(span=ema_window, adjust=False).mean()
    was_choppy = (ci >= chop_high_zone).rolling(chop_lookback, min_periods=1).max().astype(bool)
    now_falling_below = ci < chop_high_zone
    falling_edge = was_choppy.shift(1).fillna(False) & now_falling_below

    donchian_high = close.rolling(donchian_window).max().shift(1)
    breakout = close > donchian_high

    uptrend = close > ema

    entry_signal = falling_edge & breakout & uptrend
    exit_trend_break = close < ema
    exit_chop_revert = ci >= chop_high_zone

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(len(close)):
        if not in_pos:
            if bool(entry_signal.iloc[i]):
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
        else:
            held = i - entry_idx
            if bool(exit_trend_break.iloc[i]) or bool(exit_chop_revert.iloc[i]) or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    chop_window: int = 14,
    chop_high_zone: float = 61.8,
    chop_lookback: int = 10,
    ema_window: int = 50,
    donchian_window: int = 20,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no txn costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        chop_window=chop_window,
        chop_high_zone=chop_high_zone,
        chop_lookback=chop_lookback,
        ema_window=ema_window,
        donchian_window=donchian_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)

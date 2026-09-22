"""Strategy: Ultimate Oscillator (UO) bullish-divergence breakout, per Larry
Williams' original divergence rule set.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-036):
Source: Google AI Overview synthesis (Korean-language SERP; search
"Ultimate Oscillator divergence trading strategy specific rule backtest"),
read via browser_exec Google SERP fallback (web_search DDGS backend
errored this iteration). Disclosed rule set (Larry Williams' original UO
divergence rules):
  - UO(7,14,28): weighted sum of 3 periods' buying-pressure/true-range
    ratios in a 4:2:1 weighting (standard formula), most reliable on daily
    bars.
  - Bullish divergence: price makes a lower low at the most recent swing
    vs. the prior swing low, while UO makes a HIGHER low at the same two
    points.
  - Entry trigger: UO breaks above the intermediate peak (the local UO
    high between the two divergence lows) -- confirmation, not the
    divergence point itself.
  - Exit: UO crosses above 50 then back below 45 (momentum fade), OR UO
    reaches the opposite extreme (70, overbought).
No prior entry in this KB uses "Ultimate Oscillator divergence" (checked
via strategies_index.jsonl grep: zero prior matches; 13 generic "Ultimate
Oscillator" mentions use threshold-crossing mechanisms, not this specific
swing-divergence + confirmation-breakout structure, which mirrors the
already-tested-and-rejected OBV divergence design (2026-09-23-030) but on
a fundamentally different indicator (multi-period weighted momentum
oscillator vs. cumulative volume).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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


def _ultimate_oscillator(
    df: pd.DataFrame, p1: int = 7, p2: int = 14, p3: int = 28
) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    bp = close - pd.concat([low, prev_close], axis=1).min(axis=1)
    tr = pd.concat([high, prev_close], axis=1).max(axis=1) - pd.concat(
        [low, prev_close], axis=1
    ).min(axis=1)

    avg1 = bp.rolling(p1).sum() / tr.rolling(p1).sum().replace(0.0, pd.NA)
    avg2 = bp.rolling(p2).sum() / tr.rolling(p2).sum().replace(0.0, pd.NA)
    avg3 = bp.rolling(p3).sum() / tr.rolling(p3).sum().replace(0.0, pd.NA)

    uo = 100 * (4 * avg1 + 2 * avg2 + avg3) / 7
    return uo.fillna(50.0)


def _swing_lows(close: pd.Series, window: int) -> pd.Series:
    roll_min = close.rolling(window * 2 + 1, center=True).min()
    return close == roll_min


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    lookback_bars: int = 30,
    exit_cross_above: float = 50.0,
    exit_cross_below: float = 45.0,
    overbought_exit: float = 70.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    uo = _ultimate_oscillator(df)
    is_swing_low = _swing_lows(close, swing_window)

    swing_idx = [i for i, v in enumerate(is_swing_low.values) if bool(v)]
    n = len(close)
    entries = np.zeros(n, dtype=bool)

    for k in range(1, len(swing_idx)):
        i_prev, i_cur = swing_idx[k - 1], swing_idx[k]
        if i_cur - i_prev > lookback_bars or i_cur - i_prev < 2:
            continue
        price_prev, price_cur = close.iloc[i_prev], close.iloc[i_cur]
        uo_prev, uo_cur = uo.iloc[i_prev], uo.iloc[i_cur]
        if price_cur < price_prev and uo_cur > uo_prev:
            uo_peak = uo.iloc[i_prev:i_cur + 1].max()
            search_end = min(i_cur + lookback_bars, n)
            for j in range(i_cur + 1, search_end):
                if uo.iloc[j] > uo_peak:
                    entries[j] = True
                    break

    pos_vals = np.zeros(n, dtype=int)
    in_pos = False
    was_above_50 = False
    for i in range(n):
        u = uo.iloc[i]
        if in_pos:
            if u > exit_cross_above:
                was_above_50 = True
            exit_now = (was_above_50 and u < exit_cross_below) or u >= overbought_exit
            if exit_now:
                in_pos = False
                was_above_50 = False
        if not in_pos and entries[i]:
            in_pos = True
            was_above_50 = False
        pos_vals[i] = 1 if in_pos else 0

    return pd.Series(pos_vals, index=close.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    lookback_bars: int = 30,
    exit_cross_above: float = 50.0,
    exit_cross_below: float = 45.0,
    overbought_exit: float = 70.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        swing_window=swing_window,
        lookback_bars=lookback_bars,
        exit_cross_above=exit_cross_above,
        exit_cross_below=exit_cross_below,
        overbought_exit=overbought_exit,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = (position.shift(1).fillna(0) * daily_ret).fillna(0.0)
    return strat_ret

"""Strategy: Wilder Accumulative Swing Index (ASI) zero-line cross trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-131):
Per cTrader's built-in indicator documentation for the Accumulative Swing
Index (ASI, J. Welles Wilder, "New Concepts in Technical Trading Systems",
1978): ASI_t = ASI_{t-1} + SI_t, where SI_t (the Swing Index) measures each
bar's price-swing strength from OHLC changes bar-to-bar. Per that source's
stated Application section: "Buy signal - traders may consider entering a
buy position when the ASI crosses above zero, indicating increasing
bullish momentum... Sell signal - a sell position might be considered when
the ASI crosses below zero." Stop-loss placement per the same source:
"just below the last low in the ASI for long positions." This is a
genuinely new indicator family in this repo (Wilder's original 1978
swing-index construction, distinct from his other indicators RSI/ADX/ATR
already tested extensively, and distinct from all previously-tested
oscillator-zero-cross strategies since ASI's swing-index formula uses
open/high/low/close jointly with a limit-move constant, not a simple
price/volume ratio).

Swing Index formula (Wilder, standard form used across all sources that
give the calculation, e.g. cTrader/Investopedia/QuantifiedStrategies):
    K = max(|H_t - C_{t-1}|, |L_t - C_{t-1}|)
    R = TR component depending on which of the three price-range cases
        applies (H_t vs C_{t-1}, L_t vs C_{t-1}) -- the classic Wilder "R"
        selection logic below.
    SI_t = 50 * ((C_t - C_{t-1}) + 0.5*(C_t - O_t) + 0.25*(C_{t-1} - O_{t-1}))
           / R * (K / limit_move)
    ASI_t = ASI_{t-1} + SI_t

Signal logic
------------
- Compute ASI over the full history.
- Long entry: ASI (smoothed by asi_ma_window-bar SMA, to reduce whipsaw on
  the inherently noisy raw SI term) crosses from <=0 to >0 (per source:
  "ASI crosses above zero").
- Exit: ASI (smoothed) crosses back below 0, or a max_hold_days time-stop,
  or a stop-loss at stop_atr_mult * ATR(14) below entry (source: "stop
  just below the last low" -- approximated with ATR-based sizing here for
  a systematic, symbol-independent rule as elsewhere in this repo).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series {0,1} long/flat
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


def _atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window, min_periods=window).mean()


def _swing_index(df: pd.DataFrame, limit_move: float) -> pd.Series:
    """Wilder's Swing Index (SI), classic formulation."""
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    c_prev = c.shift(1)
    o_prev = o.shift(1)

    hc = (h - c_prev).abs()
    lc = (l - c_prev).abs()
    hl = (h - l).abs()
    ho_prev = (h - o_prev).abs()
    lo_prev = (l - o_prev).abs()

    k = pd.concat([hc, lc], axis=1).max(axis=1)

    # Wilder's R selection: which of the three price-range cases applies.
    cond1 = (hc >= lc) & (hc >= hl)
    cond2 = (lc >= hc) & (lc >= hl)
    r = pd.Series(np.nan, index=df.index)
    r = r.where(~cond1, hc - 0.5 * lc + 0.25 * ho_prev)
    r = r.where(~(cond2 & ~cond1), lc - 0.5 * hc + 0.25 * lo_prev)
    fallback = hl + 0.25 * (c_prev - o_prev).abs()
    r = r.where(cond1 | cond2, fallback)
    r = r.replace(0, np.nan)

    num = (c - c_prev) + 0.5 * (c - o) + 0.25 * (c_prev - o_prev)
    si = 50.0 * (num / r) * (k / limit_move)
    return si.fillna(0.0)


def _asi(df: pd.DataFrame, limit_move: float) -> pd.Series:
    si = _swing_index(df, limit_move)
    return si.cumsum()


def generate_signals(
    price_df: pd.DataFrame,
    limit_move: float = 3.0,
    asi_ma_window: int = 5,
    max_hold_days: int = 20,
    stop_atr_mult: float = 2.5,
    atr_window: int = 14,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    asi = _asi(df, limit_move)
    asi_smooth = asi.rolling(asi_ma_window, min_periods=asi_ma_window).mean()

    cross_up = (asi_smooth > 0) & (asi_smooth.shift(1) <= 0)
    cross_down = (asi_smooth < 0) & (asi_smooth.shift(1) >= 0)

    atr = _atr(df, atr_window)

    pos = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = None
    stop_price = None

    idx = df.index
    for i in range(len(idx)):
        if in_pos:
            days_held = i - entry_idx
            hit_stop = close.iloc[i] <= stop_price if stop_price is not None else False
            hit_time = days_held >= max_hold_days
            hit_cross_down = bool(cross_down.iloc[i])
            if hit_stop or hit_time or hit_cross_down:
                in_pos = False
                pos.iloc[i] = 0
            else:
                pos.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
                in_pos = True
                entry_idx = i
                a = atr.iloc[i]
                stop_price = close.iloc[i] - stop_atr_mult * a if pd.notna(a) else None
                pos.iloc[i] = 1
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    limit_move: float = 3.0,
    asi_ma_window: int = 5,
    max_hold_days: int = 20,
    stop_atr_mult: float = 2.5,
    atr_window: int = 14,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        limit_move=limit_move,
        asi_ma_window=asi_ma_window,
        max_hold_days=max_hold_days,
        stop_atr_mult=stop_atr_mult,
        atr_window=atr_window,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret

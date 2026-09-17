"""Strategy: ATR-Normalized Flag/Pole Detection with Linear-Regression-Slope
Consolidation Filter (Markos Katsanos, "Detecting Flags In Intraday Charts",
TASC December 2014), read this iteration via browser_exec at
https://traders.com/Documentation/FEEDbk_docs/2014/12/TradersTips.html
(exact TradeStation EasyLanguage strategy code disclosed directly in the
Traders' Tips section, after web_search DDGS backend errored on prior
queries this run -- direct traders.com archive URL navigation used to a
previously-unvisited TASC month, discovered by walking forward from
adjacent months already in this repo's visited_urls.jsonl ledger).

Hypothesis (see knowledge_base/strategies_log.jsonl entry for this id):
Katsanos' flag/pole pattern is a QUANTIFIED, ATR-normalized precise
definition -- distinct from this repo's prior qualitative flag/pennant
entries (Bull Flag 2026-09-08-130, Pennant 2026-09-10-004, High & Tight
Flag 2026-09-10-017, all using simple percentage-retracement or Bulkowski
qualitative rules) because it: (1) detects the "pole" (impulse move) via a
rolling highest-close-bar search and requires the pole height exceed
`pole_min_atr` x ATR(40), (2) detects the "flag" (post-pole consolidation)
via a bounded duration search where the flag's high-low range must be
LESS than `flag_max_atr` x ATR(40) AND the flag's own linear-regression
slope of Close is non-positive (i.e. flat-to-down, textbook flag
consolidation, not a further breakout), (3) requires a rising-volatility
confirmation (`ATR(40)` now vs `ATR(40)` at the pole's start must have
increased by at least `atr_min_pct`%), and (4) requires the uptrend
leading into the pole (pole bottom above the `uptrend_lookback`-day low) to
be a genuine new low broken. Entry triggers on breakout above the flag's
high. Adapted from Katsanos' intraday framing to daily bars per this
repo's established convention (2026-09-08-130 Bull Flag precedent) since
the underlying flag-geometry logic is timeframe-agnostic.

Exit (adapted, simplified from the source's multi-exit TradeStation code):
a profit target of `k_target` x pole-height-percent above entry, an ATR
stop below the flag low, a trailing stop (`atr_trail` x ATR(40) off the
`trail_bars`-day high), or a `max_hold_days` time-stop -- whichever comes
first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
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
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat(
        [h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _lin_reg_slope_at(close_window: np.ndarray) -> float:
    n = len(close_window)
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    y_mean = close_window.mean()
    denom = ((x - x_mean) ** 2).sum()
    if denom == 0:
        return 0.0
    num = ((x - x_mean) * (close_window - y_mean)).sum()
    return num / denom


def generate_signals(
    price_df: pd.DataFrame,
    max_flag_dur: int = 15,
    flag_max_atr: float = 2.5,
    pole_lookback: int = 23,
    uptrend_lookback: int = 70,
    pole_min_atr: float = 5.5,
    atr_min_pct: float = 5.0,
    atr_window: int = 40,
    k_target: float = 1.2,
    atr_stop: float = 3.0,
    atr_trail: float = 3.0,
    trail_bars: int = 5,
    max_hold_days: int = 100,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the ATR-normalized
    flag/pole breakout rule (daily-bar adaptation)."""
    df = _prep(price_df)
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    n = len(df)

    atr40 = _atr(df, atr_window).values

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_price = 0.0
    entry_bar = -1
    flag_low_at_entry = 0.0
    pole_height_pct_at_entry = 0.0

    min_hist = max(pole_lookback + max_flag_dur, uptrend_lookback, atr_window) + 2

    for i in range(min_hist, n):
        if in_position:
            bars_held = i - entry_bar
            profit_target_price = entry_price * (1 + k_target * pole_height_pct_at_entry / 100.0)
            hit_target = close[i] >= profit_target_price
            hit_stop = low[i] <= flag_low_at_entry - atr_stop * atr40[i] if not np.isnan(atr40[i]) else False
            trail_high = np.max(close[max(0, i - trail_bars) : i]) if i - trail_bars >= 0 else np.max(close[:i]) if i > 0 else close[i]
            hit_trail = (not np.isnan(atr40[i])) and close[i] < trail_high - atr_trail * atr40[i]
            hit_time = bars_held > max_hold_days
            if hit_target or hit_stop or hit_trail or hit_time:
                in_position = False
                position[i] = 0
            else:
                position[i] = 1
            continue

        # look for a flag setup ending "now" (bar i is the potential
        # breakout confirmation bar, mirroring the EasyLanguage's
        # next-bar-stop-order semantics approximated here as same-bar entry
        # signal for simplicity)
        x1 = int(np.argmax(close[i - max_flag_dur : i])) + (i - max_flag_dur)
        flag_dur_ex_pole = i - x1  # bars since the flag-window's highest close
        if flag_dur_ex_pole < 2 or flag_dur_ex_pole > max_flag_dur:
            continue

        x2 = flag_dur_ex_pole + 1
        window_start = i - x2
        if window_start < 0:
            continue
        flag_window_close = close[window_start:i]
        lf = flag_window_close.min()
        top = close[window_start : i - 1].max() if i - 1 > window_start else close[window_start:i].max()

        slope_x1 = _lin_reg_slope_at(close[i - x1 - 1 : i]) if (i - x1 - 1) >= 0 else 0.0
        # slope over the flag-duration window (approx of LinearRegSlope(Close, X1))
        slope_flag = _lin_reg_slope_at(close[max(0, i - flag_dur_ex_pole) : i])

        atrv = atr40[i]
        if np.isnan(atrv) or atrv <= 0:
            continue

        flag_range_ok = (top - lf) < flag_max_atr * atrv
        slope_ok = (slope_flag < 0) or (slope_x1 < 0)
        if not (flag_range_ok and slope_ok):
            continue

        pole_start = max(0, i - (pole_lookback + x2))
        pole_window_close = close[pole_start:i]
        y23_rel = int(np.argmin(pole_window_close))  # bars from pole_start to pole bottom
        bottom = pole_window_close.min()
        pole_height = top - bottom
        pole_min_ok = pole_height > pole_min_atr * atrv
        # Y23 (absolute index of pole bottom) must be earlier than the flag
        # window start (Y23 > X2 in EasyLanguage's bars-ago convention)
        pole_bottom_abs_idx = pole_start + y23_rel
        y23_ok = pole_bottom_abs_idx < window_start

        if not (pole_min_ok and y23_ok):
            continue

        uptrend_lo = low[max(0, i - uptrend_lookback) : i].min()
        upt1 = bottom - uptrend_lo
        uptrend_ok = upt1 > 0

        atr_at_pole_bottom = atr40[pole_bottom_abs_idx] if pole_bottom_abs_idx < len(atr40) else np.nan
        if np.isnan(atr_at_pole_bottom) or atr_at_pole_bottom <= 0:
            continue
        vol_increase_pct = (atrv / atr_at_pole_bottom - 1.0) * 100.0
        vol_ok = vol_increase_pct > atr_min_pct

        if pole_min_ok and y23_ok and uptrend_ok and vol_ok and flag_range_ok and slope_ok:
            flag_high = close[window_start:i].max()
            if close[i] > flag_high:
                in_position = True
                entry_price = close[i]
                entry_bar = i
                flag_low_at_entry = lf
                pole_height_pct_at_entry = (pole_height / (bottom + 1e-4)) * 100.0
                position[i] = 1

    return pd.Series(position, index=df.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

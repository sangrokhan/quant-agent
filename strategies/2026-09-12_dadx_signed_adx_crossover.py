"""Strategy: Harrington Dynamic ADX Histogram (DADX) signed-ADX threshold crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Neil Jon Harrington's "Revisualizing The ADX Oscillator" (TASC December
2024 Traders' Tips, fully disclosed Pine v5 source at
https://www.tradingview.com/script/8i1HxfZL-TASC-2024-12-Dynamic-ADX-Histogram/):
Wilder's classic ADX only measures trend STRENGTH, discarding direction,
which the author argues is often misapplied/misread. Harrington's Dynamic
ADX Histogram (DADX) recombines ADX with the sign of DMI+ minus DMI- to
produce a single SIGNED oscillator: DADX = +ADX when DMI+ >= DMI-
(net-bullish directional dominance), DADX = -ADX when DMI+ < DMI-
(net-bearish). This preserves both trend strength (magnitude) and
direction (sign) in one number. The source discloses only the indicator
(a color-coded histogram visualization), not a concrete trading rule --
this strategy tests the natural signal implied by the construction: DADX
crossing above a low threshold (genuine upward trend strengthening past a
noise floor, since ADX itself needs to clear some minimum to mean
anything) as a long entry, with exit on DADX falling back below that
threshold or flipping negative (directional dominance reversing to
bearish).

Signal logic
------------
- DMI+ (DIP), DMI- (DIN), ADX (DIA) via Wilder's standard formula, length
  `adx_length` (source default 10, distinct from the classic ADX 14).
- NET = DIP - DIN (directional dominance sign).
- DADX = DIA if NET >= 0, else -DIA (signed ADX).
- Long entry: DADX crosses above `adx_thresh_lo` (bullish, strengthening
  beyond the noise floor).
- Exit: DADX crosses back below `adx_thresh_lo`, or a `max_hold_days`
  time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _wilder_dmi_adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int):
    """Standard Wilder DMI+/DMI-/ADX (Wilder smoothing = ewm alpha=1/length)."""
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=high.index)

    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean() / atr.replace(0.0, np.nan)
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean() / atr.replace(0.0, np.nan)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    adx = dx.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()

    return plus_di, minus_di, adx


def generate_signals(
    price_df: pd.DataFrame,
    adx_length: int = 10,
    adx_thresh_lo: float = 20.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    plus_di, minus_di, adx = _wilder_dmi_adx(high, low, close, adx_length)
    net = plus_di - minus_di
    dadx = adx.where(net >= 0, -adx)

    above = dadx > adx_thresh_lo
    cross_up = above & (~above.shift(1).fillna(False))
    cross_down = (~above) & above.shift(1).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

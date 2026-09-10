"""Strategy: Supertrend (ATR-band flip) long-only, gated by an ADX(14)
trend-strength filter (only take Supertrend entries while ADX confirms a
genuinely trending, non-choppy market).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-120):
Per a Google AI-overview synthesis (Quantzee/FXNX sourced) of "SuperTrend +
ADX filter" strategy guides: pair Supertrend (ATR period 10, multiplier
3.0, standard params) with an ADX(14) trend-strength filter, only taking
Supertrend's bullish-flip long entries when ADX > 25 (source's stated
threshold: "Values above 25 confirm a valid trend; values below 25
indicate a ranging or choppy market" where Supertrend is prone to
whipsaws). This repo already has 7 prior SuperTrend variants (plain flip
2026-09-03-014/2026-09-04-053, RSI dual-confirmation 2026-09-06-095,
choppiness-gated 2026-09-09, vol-regime-gated 2026-09-09-010, chandelier
dual-confirm) but NONE combine it with ADX specifically -- ADX measures
directional trend strength via +DI/-DI divergence, mechanically distinct
from both the RSI-momentum gate (2026-09-06-095) and the realized-vol
regime gate (2026-09-09-010) already tried, and distinct from the
Choppiness Index gate (2026-09-09, a range-vs-trend gauge built from
ATR-sum-over-true-range rather than directional-movement smoothing).

Signal logic
------------
- Supertrend flip mechanic identical to 2026-09-04-053 (ATR bands around
  HL2, stop-and-reverse flip). Bullish regime = long-eligible.
- ADX(adx_period) computed via standard Wilder smoothing of +DM/-DM.
- Entry/hold: long only while (Supertrend bullish) AND (ADX > adx_threshold).
- Exit: Supertrend flips bearish OR ADX drops back at or below
  adx_threshold (source's own framing: ADX<25 signals the trend regime
  itself has broken down, not just a wait-and-see filter).
- Flat otherwise; long-only, no shorting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
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
    return tr.rolling(period).mean()


def _wilder_atr(df: pd.DataFrame, period: int) -> pd.Series:
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
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low = df["high"], df["low"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index
    )
    atr = _wilder_atr(df, period)
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean() / atr.replace(0.0, np.nan)
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean() / atr.replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    adx = dx.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    return adx.fillna(0.0)


def _supertrend(df: pd.DataFrame, atr_period: int = 10, multiplier: float = 3.0) -> pd.Series:
    """Return a boolean series: True = bullish (in lower-band regime)."""
    high, low, close = df["high"], df["low"], df["close"]
    hl2 = (high + low) / 2.0
    atr = _atr(df, atr_period)
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    idx = df.index
    final_upper = pd.Series(index=idx, dtype=float)
    final_lower = pd.Series(index=idx, dtype=float)
    bullish = pd.Series(index=idx, dtype=bool)

    first_valid_pos = atr.first_valid_index()
    if first_valid_pos is None:
        return pd.Series(False, index=idx)
    start_pos = list(idx).index(first_valid_pos)

    final_upper.iloc[start_pos] = basic_upper.iloc[start_pos]
    final_lower.iloc[start_pos] = basic_lower.iloc[start_pos]
    bullish.iloc[start_pos] = close.iloc[start_pos] > final_upper.iloc[start_pos]

    for i in range(start_pos + 1, len(idx)):
        bu = basic_upper.iloc[i]
        bl = basic_lower.iloc[i]
        prev_fu = final_upper.iloc[i - 1]
        prev_fl = final_lower.iloc[i - 1]
        prev_close = close.iloc[i - 1]

        fu = bu if (bu < prev_fu or prev_close > prev_fu) else prev_fu
        fl = bl if (bl > prev_fl or prev_close < prev_fl) else prev_fl
        final_upper.iloc[i] = fu
        final_lower.iloc[i] = fl

        prev_bull = bullish.iloc[i - 1]
        cur_close = close.iloc[i]
        if prev_bull:
            bullish.iloc[i] = cur_close > fl
        else:
            bullish.iloc[i] = cur_close > fu

    return bullish.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    atr_period: int = 10,
    multiplier: float = 3.0,
    adx_period: int = 14,
    adx_threshold: float = 25.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    bullish = _supertrend(df, atr_period=atr_period, multiplier=multiplier)
    adx = _adx(df, period=adx_period)
    trending = adx > adx_threshold
    position = (bullish & trending).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

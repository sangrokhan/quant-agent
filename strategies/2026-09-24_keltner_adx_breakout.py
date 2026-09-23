"""Strategy: Keltner Channel breakout, confirmed by ADX trend-strength filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-013):
Per Shubham Chaudhary's "Keltner Channel Breakout + ADX Confirmation"
(LinkedIn, Mar 2025,
https://www.linkedin.com/pulse/keltner-channel-breakout-adx-confirmation-shubham-chaudhary-vy8wf):
Keltner Channel = SMA(period) +/- ATR(period)*atr_mult (source default
period=20, atr_mult=2). A close above the upper band with ADX(adx_period)
> adx_threshold (source default 25) signals a strong bullish breakout
worth a long entry (source's own symmetric system also shorts on a
lower-band breakout -- dropped here, long-only per SAFETY.md). Exit when
price touches the opposite (lower) band or via a max_hold_days time-stop
(the source's own written exit rule is "price touches the opposite band",
adapted with a time-stop safety net since a long-only variant has no
natural symmetric exit trigger without the short side). Source's own
backtest (NASDAQ/GBPUSD/Bitcoin, timeframe unspecified): ~65% win rate,
MDD ~4.2%. This repo has 2 prior plain-Keltner entries (no ADX combo) and
9 prior ADX entries (no Keltner combo) -- first Keltner+ADX breakout
combo in this repo.

Signal logic
------------
- Keltner midline = SMA(period); ATR(period) via Wilder's method (simple
  rolling mean of true range, a standard simplification).
- upper_band = midline + atr_mult * ATR; lower_band = midline - atr_mult * ATR.
- ADX(adx_period) computed via the standard Wilder DI+/DI-/DX/ADX chain.
- Entry (long): close crosses above upper_band AND ADX > adx_threshold.
- Exit: close crosses back below lower_band, OR max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    tr = _true_range(df)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _adx(df: pd.DataFrame, period: int) -> pd.Series:
    high, low = df["high"], df["low"]
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = _true_range(df)
    atr = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    plus_dm_s = pd.Series(plus_dm, index=df.index).ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    minus_dm_s = pd.Series(minus_dm, index=df.index).ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    plus_di = 100 * (plus_dm_s / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm_s / atr.replace(0, np.nan))

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    kc_period: int = 20,
    atr_mult: float = 2.0,
    adx_period: int = 14,
    adx_threshold: float = 25.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    midline = close.rolling(kc_period).mean()
    atr = _atr(df, kc_period)
    upper_band = midline + atr_mult * atr
    lower_band = midline - atr_mult * atr
    adx = _adx(df, adx_period)

    above_upper = close > upper_band
    prev_above_upper = above_upper.shift(1).fillna(False)
    breakout_up = above_upper & (~prev_above_upper)

    strong_trend = adx > adx_threshold
    entry = breakout_up & strong_trend.fillna(False)
    exit_lower = close < lower_band

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_lower.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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

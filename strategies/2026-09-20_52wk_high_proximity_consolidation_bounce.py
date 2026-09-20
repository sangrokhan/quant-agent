"""Strategy: 52-Week High Proximity + Trend Stack + ATR Consolidation + Bounce Trigger.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-128):
Per EasySwing.trading's "52-Week High Pullback" strategy deep-dive
(https://easyswing.trading/blog/52-week-high-pullback-swing-trading, visited
via browser_exec this iteration -- web_search backend errored with
RequestError/rustls TLS EOF for every query this iteration), stocks near
their 52-week high (George & Hwang 2004 anchoring-bias anomaly) that are
ALSO in a confirmed intermediate uptrend, consolidating (a low-range pause
rather than continued volatility), and then bounce off that pause tend to
keep advancing. The source's own implementation is cross-sectional
(requires an RS-rank>=80 versus a tracked universe, which this repo's
single-symbol generate_returns_fn architecture cannot compute) -- this
adaptation drops the cross-sectional RS-rank gate and keeps the six
single-symbol-computable gates: (1) close > SMA50 > SMA200 trend stack,
(2) SMA50 rising over the trailing 5 bars, (3) close within X% of the
252-session rolling high, (4) that proximity improving (not worse) versus
20 sessions ago, (5) ADX(14) >= a trend-strength floor, (6) today's true
range <= a fraction of ATR14 (consolidation/pause signature). Entry
triggers the NEXT bar after all six gates hold AND a bounce candle confirms
on the gate day itself (today's high > prior high, today's close > prior
close, close in the upper half of today's range) -- entering long at the
next day's open-equivalent (we use next-bar's return, i.e. shift(1) like
every other strategy in this repo, to avoid look-ahead). Exit on ATR-based
trailing stop or a max holding period (this repo's simplification of the
source's fixed ATR-multiple initial stop, since a dynamic profit-target
ladder isn't part of the vectorbt-return-series contract used here).

Signal logic
------------
- trend gate: close > SMA(sma_fast) > SMA(sma_slow), AND SMA(sma_fast) is
  higher than it was 5 bars ago (rising).
- proximity gate: close / rolling(hi_lookback).max() >= (1 - near_high_pct),
  AND that same "closeness" ratio today is no more than
  proximity_tolerance_pct worse than it was 20 bars ago (improving/flat,
  not deteriorating).
- trend-strength gate: ADX(adx_window) >= adx_floor (simplified Wilder ADX).
- consolidation gate: today's true range <= consolidation_atr_frac *
  ATR(atr_window).
- bounce trigger (same bar as the gates above): today's high > yesterday's
  high, today's close > yesterday's close, AND close in the upper half of
  today's [low, high] range.
- Entry: long starting the NEXT bar once bounce triggers (avoids look-ahead
  -- generate_returns() shifts position by 1 already, so signaling on the
  bounce-candle bar itself is the correct "signal today, trade tomorrow"
  convention used throughout this repo).
- Exit: close crosses below a chandelier-style trailing stop
  (rolling max close since entry - stop_atr_mult * ATR14), OR after
  max_hold_days bars, whichever comes first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def _adx(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean() / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean() / atr.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    return adx.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    sma_fast: int = 50,
    sma_slow: int = 200,
    hi_lookback: int = 252,
    near_high_pct: float = 0.07,
    proximity_tolerance_pct: float = 0.02,
    adx_window: int = 14,
    adx_floor: float = 20.0,
    atr_window: int = 14,
    consolidation_atr_frac: float = 0.70,
    stop_atr_mult: float = 2.26,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma_fast_s = close.rolling(sma_fast).mean()
    sma_slow_s = close.rolling(sma_slow).mean()
    trend_stack = (close > sma_fast_s) & (sma_fast_s > sma_slow_s)
    sma_fast_rising = sma_fast_s > sma_fast_s.shift(5)

    rolling_high = close.rolling(hi_lookback, min_periods=max(20, hi_lookback // 4)).max()
    closeness = close / rolling_high
    near_high = closeness >= (1.0 - near_high_pct)
    proximity_improving = closeness >= (closeness.shift(20) - proximity_tolerance_pct)

    adx = _adx(df, adx_window)
    adx_gate = adx >= adx_floor

    atr = _atr(df, atr_window)
    true_range = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    consolidating = true_range <= (consolidation_atr_frac * atr)

    bounce = (high > high.shift(1)) & (close > close.shift(1))
    upper_half = close >= (low + (high - low) * 0.5)

    all_gates = trend_stack & sma_fast_rising & near_high & proximity_improving & adx_gate & consolidating
    entry_trigger = (all_gates & bounce & upper_half).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    peak_close = 0.0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            peak_close = max(peak_close, close.iloc[i])
            atr_i = atr.iloc[i] if not pd.isna(atr.iloc[i]) else 0.0
            trail_stop = peak_close - stop_atr_mult * atr_i
            if close.iloc[i] < trail_stop or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                peak_close = close.iloc[i]
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret

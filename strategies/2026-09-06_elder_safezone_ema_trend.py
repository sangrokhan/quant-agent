"""Strategy: EMA trend-turn entry with Elder SafeZone trailing-stop exit.

Hypothesis (see knowledge_base/strategies_log.jsonl):
Dr. Alexander Elder's SafeZone Stop estimates directional market noise from
recent counter-trend penetrations (how far the low dips below the prior
low during an uptrend) and places a trailing stop beyond `factor` times
that average noise -- a noise-adaptive stop distance rather than a fixed
ATR multiple. Per pineify.app's Elder SafeZone Stop explainer
(https://pineify.app/algorithmic-trading/elder-safezone-stop): "longNoise
= average(max(previousLow - currentLow, 0))" over a lookback window;
"longCandidate = referencePrice - factor * longNoise"; the stop follows a
one-way trailing rule ("A long stop should not move down while the long
trend state remains active... use the tighter of the previous stop and
current candidate").

Because the SafeZone stop widens automatically during genuinely noisy
(large recent counter-trend dips) conditions and tightens during calm
trending conditions, it should give a trend-following entry more room to
breathe in choppy uptrends while still cutting losses faster than a fixed
stop once the trend genuinely quiets down and then reverses.

First Elder-SafeZone strategy in this repo -- distinct from all ATR-based
trailing stops already tested (Chandelier Exit, SuperTrend, Chande Kroll
Stop) since SafeZone's noise measure is derived purely from counter-trend
low-penetration distances, not the True Range/ATR statistic.

Signal logic
------------
- Trend gate: EMA(trend_span) turning from non-rising to rising (EMA
  slope flip up) signals a long entry.
- SafeZone trailing stop: longNoise[t] = rolling mean over
  `safezone_lookback` bars of max(low[t-1]-low[t], 0); stop candidate[t] =
  close[t] - safezone_factor * longNoise[t]; the actual trailing stop is
  the running maximum of all candidates since entry (one-way ratchet,
  never loosens).
- Exit: close crosses below the trailing SafeZone stop, the EMA turns down
  (slope flip), or a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    ema_span: int = 20,
    safezone_lookback: int = 20,
    safezone_factor: float = 2.5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    ema = close.ewm(span=ema_span, adjust=False).mean()
    ema_rising = ema > ema.shift(1)
    entry_trigger = ema_rising & (~ema_rising.shift(1).fillna(False))
    trend_turn_down = (~ema_rising) & (ema_rising.shift(1).fillna(False))

    penetration = (low.shift(1) - low).clip(lower=0.0)
    long_noise = penetration.rolling(safezone_lookback).mean()
    candidate = close - safezone_factor * long_noise

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    trailing_stop = None
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            cand = candidate.iloc[i]
            if trailing_stop is None or (pd.notna(cand) and cand > trailing_stop):
                trailing_stop = cand
            stop_hit = trailing_stop is not None and pd.notna(trailing_stop) and close.iloc[i] < trailing_stop
            if stop_hit or bool(trend_turn_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                trailing_stop = None
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                trailing_stop = candidate.iloc[i] if pd.notna(candidate.iloc[i]) else None
                position.iloc[i] = 1

    position.name = "position"
    return position


def generate_returns(
    price_df: pd.DataFrame,
    ema_span: int = 20,
    safezone_lookback: int = 20,
    safezone_factor: float = 2.5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df, ema_span=ema_span, safezone_lookback=safezone_lookback,
        safezone_factor=safezone_factor, max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns

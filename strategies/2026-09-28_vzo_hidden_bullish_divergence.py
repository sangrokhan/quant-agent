"""Strategy: Volume Zone Oscillator (VZO) Hidden Bullish Divergence
continuation, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-28-042),
sourced from https://www.liqtheory.com/learn/course-4-liquidity-theory/fsvzo-volume-zone-oscillator
(Liquidity Theory's FSVZO course lesson, read via browser_exec -- web_extract
ddgs backend is search-only and cannot extract URL content).

The source discloses FOUR concrete divergence types for the Volume Zone
Oscillator (VZO, Khalil & Steckler 2009/2011, already implemented in this
repo's `strategies/2026-09-04_vzo_oversold_trend_gate.py` -- reused here
verbatim, no re-derivation):
  - Regular Bullish: price lower low, VZO higher low -> REVERSAL up
  - Regular Bearish: price higher high, VZO lower high -> REVERSAL down
  - Hidden Bullish: price higher low, VZO lower low -> CONTINUATION up
  - Hidden Bearish: price lower high, VZO higher high -> CONTINUATION down

This repo has 5 prior VZO entries (binary oversold-threshold crossover,
zero-line crossover, and continuous z-score sizing dial variants) but NONE
use a divergence pattern as the entry trigger -- distinct mechanism from
all prior VZO work in this repo.

This iteration tests the HIDDEN BULLISH divergence specifically (source's
own framing: "H during an uptrend pullback = hidden bullish divergence
confirms pullback is over -- continuation long trigger"): price making a
higher swing low while VZO makes a LOWER swing low during a pullback within
an established uptrend signals volume-based confirmation that the pullback
has ended and the uptrend is resuming -- i.e. a trend-continuation buy,
not a reversal buy (distinct from the "regular" bullish divergence which
signals a reversal from a downtrend low).

Signal logic (daily bars, causal/no look-ahead):
1. Trend filter: close > SMA(trend_window) (default 200d) -- only trade
   continuation signals within an established uptrend, per the source's
   own "during an uptrend pullback" framing.
2. Identify local swing lows in price over a `pivot_window`-bar rolling
   window (a bar is a swing low if it's the minimum close within
   +/-pivot_window bars around it).
3. Hidden bullish divergence confirmed when: the CURRENT confirmed swing
   low's close > the PRIOR confirmed swing low's close (price higher low)
   AND the VZO value at the current swing low < the VZO value at the
   prior swing low (VZO lower low) -- exact mirror of the source's
   definition.
4. Entry (long): divergence confirmed (with `confirm_lag` bars needed to
   confirm a swing point is indeed a local min, avoiding look-ahead) AND
   trend filter holds.
5. Exit: VZO crosses back below its own EMA signal line (source's stated
   "R and H labels...provide clear, objective entry signals when combined
   with TA levels" -- since no explicit exit rule is given for the
   continuation case, we use the same VZO EMA signal-line-cross exit this
   repo's other VZO strategies use) OR trend filter breaks OR a
   max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
validation/grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def _vzo(close: pd.Series, volume: pd.Series, period: int) -> pd.Series:
    signed_volume = volume.where(close > close.shift(1), -volume)
    vp = signed_volume.ewm(span=period, min_periods=period, adjust=False).mean()
    tv = volume.ewm(span=period, min_periods=period, adjust=False).mean()
    return 100.0 * vp / tv.replace(0, float("nan"))


def _swing_lows(close: pd.Series, pivot_window: int) -> pd.Series:
    """Bool mask: True where close[i] is the min within [i-pivot_window, i+pivot_window].

    Uses a centered rolling window -- confirmed with a `pivot_window`-bar
    lag (a swing low can only be identified once `pivot_window` bars have
    passed after it, avoiding look-ahead in generate_signals below).
    """
    n = len(close)
    is_low = pd.Series(False, index=close.index)
    values = close.values
    for i in range(pivot_window, n - pivot_window):
        window = values[i - pivot_window : i + pivot_window + 1]
        if values[i] == window.min():
            is_low.iloc[i] = True
    return is_low


def generate_signals(
    price_df: pd.DataFrame,
    vzo_period: int = 14,
    trend_window: int = 200,
    pivot_window: int = 5,
    confirm_lag: int = 5,
    signal_ema_span: int = 9,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"].astype(float)

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    vzo = _vzo(close, volume, vzo_period)
    vzo_signal = vzo.ewm(span=signal_ema_span, adjust=False).mean()

    swing_low_mask = _swing_lows(close, pivot_window)
    swing_low_indices = [i for i, v in enumerate(swing_low_mask.values) if v]

    n = len(close)
    # For each bar t, find the two most recent CONFIRMED swing lows (a
    # swing low at position p is only "confirmed" once t >= p + confirm_lag,
    # i.e. confirm_lag bars have elapsed since it -- avoids look-ahead).
    divergence = pd.Series(False, index=close.index)
    vzo_values = vzo.values
    close_values = close.values

    swing_ptr = 0
    confirmed = []
    for t in range(n):
        while swing_ptr < len(swing_low_indices) and swing_low_indices[swing_ptr] + confirm_lag <= t:
            confirmed.append(swing_low_indices[swing_ptr])
            swing_ptr += 1
        if len(confirmed) >= 2:
            prev_idx, curr_idx = confirmed[-2], confirmed[-1]
            # only flag the divergence on the bar right after the current
            # swing low gets confirmed (avoid re-firing every subsequent bar)
            if curr_idx + confirm_lag == t:
                price_higher_low = close_values[curr_idx] > close_values[prev_idx]
                vzo_lower_low = (
                    not np.isnan(vzo_values[curr_idx])
                    and not np.isnan(vzo_values[prev_idx])
                    and vzo_values[curr_idx] < vzo_values[prev_idx]
                )
                if price_higher_low and vzo_lower_low:
                    divergence.iloc[t] = True

    entry = divergence & uptrend.fillna(False)

    prev_vzo = vzo.shift(1)
    prev_signal = vzo_signal.shift(1)
    exit_vzo_cross = (prev_vzo >= prev_signal) & (vzo < vzo_signal)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if (
                bool(exit_vzo_cross.iloc[i])
                or not bool(uptrend.fillna(False).iloc[i])
                or held >= max_hold_days
            ):
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

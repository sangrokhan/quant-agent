"""Strategy: Ease of Movement (EMV) bullish divergence vs. rolling swing lows.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-093):
Per https://arrowalgo.com/ease-of-movement-emv-complete-guide-algorithmic-trading/'s
"divergence strategy": "Watch for price making new lows while EMV makes
higher lows. This bullish divergence signals exhaustion in the downtrend.
Look for entry opportunities on the long side." EMV (Richard Arms) is a
volume-weighted momentum indicator = Distance Moved / Box Ratio, smoothed
by an n-period moving average (default 14) -- distinguishing it from pure
price-only oscillators since it explicitly incorporates volume via the Box
Ratio term.

This is distinct from the already-ACCEPTED plain EMV zero-line-crossover +
SMA-trend-filter strategy in this repo (2026-09-04-115, QQQ+SPY accepted) --
that strategy trades EMV's absolute zero-cross level, while this strategy
trades a DIVERGENCE between EMV and price structure at swing lows (a
distinct technique family already used elsewhere in this repo for CMF
(2026-09-05-047), Bollinger %B, Elder Bull Power, Force Index, OBV, MACD
Histogram, and Stochastic %K, but never yet applied to EMV specifically).

Concrete mechanical rule (reconstruction of the standard "divergence"
pattern applied to EMV, since the source describes the concept but not
exact swing-detection parameters -- following this repo's established CMF
divergence convention, see 2026-09-05_cmf_bullish_divergence_swinglow.py):
- A "swing low" bar is a local minimum of close over a +/-pivot_window bar
  window (only confirmable pivot_window bars later -- no lookahead).
- At the most recent confirmed swing low, compare close and smoothed EMV
  against the PRIOR swing low (within lookback_bars bars):
  - Bullish divergence = current swing low's close < prior swing low's
    close (price lower low) AND current swing low's EMV > prior swing
    low's EMV (EMV higher low).
- Entry (long): on the bar the divergence is confirmed, gated by RSI(14) <
  rsi_gate (avoid buying a fresh divergence into an already-overbought
  bounce, same convention as the CMF divergence strategy).
- Exit: close crosses back below the swing-low's close (failed bounce),
  EMV crosses back below zero (buying pressure evaporated), or a
  max_hold_days time-stop.

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


def _emv(df: pd.DataFrame, smooth_window: int) -> pd.Series:
    high, low, volume = df["high"], df["low"], df["volume"]
    midpoint = (high + low) / 2.0
    distance_moved = midpoint.diff()
    box_ratio = (volume / 1e8) / (high - low).replace(0, np.nan)
    raw_emv = (distance_moved / box_ratio).fillna(0.0)
    emv = raw_emv.rolling(smooth_window).mean()
    return emv.fillna(0.0)


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _find_swing_lows(close: pd.Series, pivot_window: int) -> pd.Series:
    n = len(close)
    is_low = pd.Series(False, index=close.index)
    c = close.to_numpy()
    for i in range(pivot_window, n - pivot_window):
        window_slice = c[i - pivot_window : i + pivot_window + 1]
        if c[i] == window_slice.min():
            is_low.iloc[i] = True
    return is_low


def generate_signals(
    price_df: pd.DataFrame,
    emv_smooth_window: int = 14,
    pivot_window: int = 5,
    lookback_bars: int = 60,
    rsi_window: int = 14,
    rsi_gate: float = 60.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    emv = _emv(df, emv_smooth_window)
    rsi = _rsi(close, rsi_window)
    swing_low = _find_swing_lows(close, pivot_window)

    swing_low_idx = np.where(swing_low.to_numpy())[0]

    entry = pd.Series(False, index=close.index)
    swing_low_close_at_confirm: dict = {}
    prior_low_idx = None
    for low_i in swing_low_idx:
        confirm_i = low_i + pivot_window
        if confirm_i >= n:
            continue
        if prior_low_idx is not None and (low_i - prior_low_idx) <= lookback_bars:
            price_lower_low = close.iloc[low_i] < close.iloc[prior_low_idx]
            emv_higher_low = emv.iloc[low_i] > emv.iloc[prior_low_idx]
            if price_lower_low and emv_higher_low and rsi.iloc[confirm_i] < rsi_gate:
                entry.iloc[confirm_i] = True
                swing_low_close_at_confirm[confirm_i] = close.iloc[low_i]
        prior_low_idx = low_i

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_swing_low_close = None
    for i in range(n):
        if in_position:
            held = i - entry_idx
            failed_bounce = entry_swing_low_close is not None and close.iloc[i] < entry_swing_low_close
            emv_evaporated = emv.iloc[i] < 0
            if failed_bounce or emv_evaporated or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                entry_swing_low_close = swing_low_close_at_confirm.get(i)
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret

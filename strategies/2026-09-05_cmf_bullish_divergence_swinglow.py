"""Strategy: Chaikin Money Flow (CMF) bullish divergence vs. rolling swing lows.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-047):
Per TradingView's own CMF documentation (Chaikin_money_flow script page,
tradingview.com/scripts/chaikin_money_flow/): "A bullish CMF divergence
occurs when the price makes a lower low, but the CMF makes a higher low
(suggesting increasing buying pressure)." This is distinct from the
already-tested CMF threshold-cross rule in this repo (2026-09-04-043,
CMF crossing above +0.05) and from the Twiggs Money Flow zero-cross
pullback rule (2026-09-05-002) -- here the signal is a divergence
between price structure and money-flow structure at swing lows, not an
absolute-level threshold cross.

Concrete mechanical rule (our own reconstruction of the standard
technical-analysis "divergence" pattern applied to CMF, since the source
describes the concept but not exact swing-detection parameters):
- A "swing low" bar is a local minimum of close over a
  +/-`pivot_window` bar window.
- At the most recent swing low, compare close and CMF(cmf_window) against
  the PRIOR swing low (within `lookback_bars` bars):
  - Bullish divergence = current swing low's close < prior swing low's
    close (price lower low) AND current swing low's CMF > prior swing
    low's CMF (CMF higher low).
- Entry (long): on the bar the current swing low is confirmed (i.e.
  `pivot_window` bars after the low, once we can confirm it was a local
  min) AND divergence is present, gated by close > SMA(trend_window)
  200-day filter is deliberately OMITTED here (source's divergence is
  explicitly meant to catch REVERSALS at the end of downtrends, so
  requiring price > 200SMA would exclude exactly the setups being
  targeted) -- instead we gate on RSI(14) < rsi_gate to require the
  broader momentum context still look oversold/neutral, avoiding buying
  a fresh divergence into an already-overbought bounce.
- Exit: close crosses back below the swing-low's close (failed bounce),
  CMF crosses back below zero (buying pressure evaporated), or a
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


def _cmf(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]
    rng = (high - low).replace(0, np.nan)
    mfm = ((close - low) - (high - close)) / rng
    mfv = (mfm * volume).fillna(0.0)
    cmf = mfv.rolling(window).sum() / volume.rolling(window).sum().replace(0, np.nan)
    return cmf.fillna(0.0)


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _find_swing_lows(close: pd.Series, pivot_window: int) -> pd.Series:
    """Boolean series: True at bar i if close[i] is the min of close[i-pivot_window:i+pivot_window+1]
    (only confirmable pivot_window bars later, so entry uses the confirmed-at bar)."""
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
    cmf_window: int = 20,
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

    cmf = _cmf(df, cmf_window)
    rsi = _rsi(close, rsi_window)
    swing_low = _find_swing_lows(close, pivot_window)

    # Confirmation happens pivot_window bars after the actual low bar.
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
            cmf_higher_low = cmf.iloc[low_i] > cmf.iloc[prior_low_idx]
            if price_lower_low and cmf_higher_low and rsi.iloc[confirm_i] < rsi_gate:
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
            cmf_evaporated = cmf.iloc[i] < 0
            if failed_bounce or cmf_evaporated or held >= max_hold_days:
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

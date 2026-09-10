"""Strategy: DeMarker (DeM) oscillator bullish-divergence long entry.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://tradersunion.com/interesting-articles/forex-indicators-for-traders/demarker-indicator/
("Divergence spotting strategy" section): "Like RSI, DeMarker can be used to
spot bullish or bearish divergence, signaling a potential trend reversal
before price shows it... Bullish divergence: Price makes a lower low, but
DeMarker makes a higher low. These setups often appear before sharp
reversals." The source also gives the DeMarker formula precisely:
DeMarker = SMA(DeMax, n) / (SMA(DeMax, n) + SMA(DeMin, n)), where
DeMax = max(high_t - high_{t-1}, 0) and DeMin = max(low_{t-1} - low_t, 0),
with default period n=14 and overbought/oversold levels 0.70/0.30.

This repo already has a DeMarker oversold-bounce threshold-crossing
strategy (2026-09-04-154, accepted narrowly on QQQ only), but no DeMarker
DIVERGENCE construction has been tested -- distinct technique (divergence
vs. threshold-cross) on the same indicator family, following this repo's
established swing-low-divergence pattern (already validated testable in
BOP/A-D-Line/Elder-Ray/MFI divergence entries).

Signal logic
------------
- DeMarker_t = SMA(DeMax, dem_window) / (SMA(DeMax, dem_window) + SMA(DeMin, dem_window)).
- Identify local swing lows in price (a close that is the minimum within a
  trailing +/- `swing_window` bar window).
- Bullish divergence: at a swing-low bar, price is LOWER than the prior
  price swing low, while DeMarker's value at the same bar is HIGHER than
  DeMarker's value at the prior price swing low (selling pressure fading
  despite the new price low).
- Entry (long): on the bar the bullish divergence is confirmed, gated by
  DeMarker < `oversold_gate` (source's 0.30 oversold zone) to keep entries
  confined to the exhaustion zone the source describes, not any divergence
  anywhere on the chart.
- Exit: close crosses back above its `exit_sma_window`-day SMA (mean
  reversion / trend re-confirmation, consistent with other divergence
  strategies in this repo), OR after `max_hold_days` (time-stop backstop).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _demarker(df: pd.DataFrame, dem_window: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    demax = (high - high.shift(1)).clip(lower=0.0)
    demin = (low.shift(1) - low).clip(lower=0.0)
    sma_demax = demax.rolling(dem_window).mean()
    sma_demin = demin.rolling(dem_window).mean()
    denom = (sma_demax + sma_demin).replace(0.0, np.nan)
    dem = sma_demax / denom
    return dem.fillna(0.5)


def generate_signals(
    price_df: pd.DataFrame,
    dem_window: int = 14,
    swing_window: int = 5,
    oversold_gate: float = 0.30,
    exit_sma_window: int = 20,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    dem = _demarker(df, dem_window=dem_window)

    n = len(close)
    is_swing_low = pd.Series(False, index=close.index)
    close_vals = close.values
    for i in range(swing_window, n - swing_window):
        window = close_vals[i - swing_window : i + swing_window + 1]
        if close_vals[i] == window.min():
            is_swing_low.iloc[i] = True

    swing_low_idxs = list(np.where(is_swing_low.values)[0])

    entry = pd.Series(False, index=close.index)
    prev_swing_i = None
    for i in swing_low_idxs:
        if prev_swing_i is not None:
            price_lower_low = close_vals[i] < close_vals[prev_swing_i]
            dem_higher_low = dem.iloc[i] > dem.iloc[prev_swing_i]
            dem_oversold = dem.iloc[i] < oversold_gate
            if price_lower_low and dem_higher_low and dem_oversold:
                entry.iloc[i] = True
        prev_swing_i = i

    sma = close.rolling(exit_sma_window).mean()
    exit_meanrev = close > sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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

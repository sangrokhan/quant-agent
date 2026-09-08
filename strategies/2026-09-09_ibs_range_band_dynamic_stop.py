"""Strategy: IBS + Rolling-Range Lower-Band Mean Reversion with dynamic
SMA stop (long-only), "the 2.11 Sharpe strategy".

Hypothesis (this iteration):
Per https://www.quantitativo.com/p/a-mean-reversion-strategy-with-211,
a quant blogger's own verified/reproduced rule set (originally tested on
SPY, later found to work much better on QQQ):

1. Compute the rolling mean of (High - Low) over the last range_window
   (25) days.
2. Compute the IBS indicator: (Close - Low) / (High - Low).
3. Compute a lower band = rolling High over the last band_window (10)
   days MINUS band_mult (2.5) x the rolling mean of (High - Low).
4. Go long whenever close is under the lower band AND IBS < ibs_threshold
   (0.3).
5. Exit whenever close > yesterday's high, OR close < SMA(stop_window)
   (a "dynamic stop loss" the source's own "Improvement 2" -- source
   found this beats both the raw rules and a market-regime-filter
   variant that cut too much return).

Source's own verified backtest result (QQQ, 1993-2024, with the dynamic
SMA(300) stop): Sharpe improved from an original-rules baseline of 1.83
to 2.11, annualized return 13.0% (vs Buy&Hold ~9%), with a materially
reduced max drawdown vs. the raw un-stopped version. This is a genuinely
distinct construction from every prior IBS-family entry in this repo
(2026-09-04-089: fixed ibs_entry/ibs_exit thresholds + a 200-SMA
proximity band, no rolling-range lower-band component at all) since the
entry condition here combines IBS with a SEPARATE price-level lower band
built from a rolling-high-minus-k*mean-range construction (distinct
statistical logic from a pure oscillator threshold), and the exit uses a
dynamic SMA-based stop rather than an IBS-reversion-to-high target.

Signal logic
------------
- range_mean = rolling mean of (High - Low) over range_window (25) days.
- ibs = (Close - Low) / (High - Low).
- lower_band = rolling max of High over band_window (10) days -
  band_mult (2.5) * range_mean.
- Entry (long): close < lower_band AND ibs < ibs_threshold (0.3).
- Exit: close > prior day's high, OR close < SMA(stop_window) (300, per
  source's own tuned "dynamic stop" experiment), OR a max_hold_days
  time-stop backstop (source's own rules have no explicit max-hold, but
  this repo's convention adds one as a safety backstop).

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

Sources:
    https://www.quantitativo.com/p/a-mean-reversion-strategy-with-211
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


def generate_signals(
    price_df: pd.DataFrame,
    range_window: int = 25,
    band_window: int = 10,
    band_mult: float = 2.5,
    ibs_threshold: float = 0.3,
    stop_window: int = 300,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    n = len(close)

    range_mean = (high - low).rolling(range_window).mean()
    ibs = (close - low) / (high - low).replace(0, np.nan)
    lower_band = high.rolling(band_window).max() - band_mult * range_mean
    sma_stop = close.rolling(stop_window).mean()

    entry_cond = ((close < lower_band) & (ibs < ibs_threshold)).fillna(False)

    c = close.to_numpy(dtype=float)
    h = high.to_numpy(dtype=float)
    sma_arr = sma_stop.to_numpy(dtype=float)
    entry_arr = entry_cond.to_numpy(dtype=bool)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            px = c[i]
            prior_high = h[i - 1] if i >= 1 else h[i]
            hit_high_exit = px > prior_high
            hit_sma_stop = (not np.isnan(sma_arr[i])) and px < sma_arr[i]
            hit_time = held >= max_hold_days
            if hit_high_exit or hit_sma_stop or hit_time:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if entry_arr[i]:
                in_position = True
                entry_idx = i
                position[i] = 1
            else:
                position[i] = 0

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret

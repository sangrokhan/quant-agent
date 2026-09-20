"""Strategy: Volume-Weighted Bollinger Bands mean reversion.

Hypothesis (this iteration):
Per Google's AI-overview synthesis (multiple corroborating TradingView
script listings, https://www.google.com/search?q=%22Volume+Weighted+Bollinger+Bands%22+strategy+formula+entry+exit+rule,
read via browser_exec this iteration -- web_search backend intermittently
TLS-erroring so browser fallback used for discovery): Volume-Weighted
Bollinger Bands (VWBB) replace the standard Bollinger Band's simple-moving-
average centerline with a Volume-Weighted Moving Average (VWMA), and the
band width uses a volume-weighted standard deviation instead of the plain
close-price std dev:

    VWMA = sum(P_i * V_i) / sum(V_i)               over `window` bars
    VW_StdDev = sqrt( sum(V_i * (P_i - VWMA)^2) / sum(V_i) )
    Upper = VWMA + D * VW_StdDev
    Lower = VWMA - D * VW_StdDev

The claimed advantage (per the TradingView listings corroborated by the AI
overview) is that VWBB is "more sensitive to volume" than a plain SMA-based
Bollinger Band -- i.e. bars with heavier volume pull the centerline/band
more strongly, so a band touch on low relative volume is treated
differently than one on high relative volume. This repo already has
VWMA-as-a-trend-crossover-line entries (2026-09-04_vwma_dual_crossover.py,
2026-09-17_vwma_vs_sma_crossover_calhoun.py) but none use VWMA as a
Bollinger-style BAND centerline with a volume-weighted std-dev band width,
which is the specific novel construction being tested here.

Signal logic
------------
- VWMA and VW_StdDev computed over a rolling `window` using volume weights
  (see formulas above).
- Entry (long): close crosses below the lower band (oversold relative to
  the volume-weighted mean) AND close > SMA(trend_window) (only mean-revert
  within an established uptrend, avoiding catching falling knives).
- Exit: close crosses back above the VWMA centerline, or a max_hold_days
  time-stop.
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals(price_df, **params) -> pd.Series {0,1};
generate_returns(price_df, **params) -> pd.Series of daily strategy returns.
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


def _vwma_and_vwstd(close: pd.Series, volume: pd.Series, window: int):
    pv = close * volume
    sum_pv = pv.rolling(window).sum()
    sum_v = volume.rolling(window).sum().replace(0, np.nan)
    vwma = sum_pv / sum_v

    # Volume-weighted variance: sum(V_i * (P_i - VWMA)^2) / sum(V_i).
    # VWMA here is the rolling value aligned to each window's end; for a
    # rolling computation we approximate using the bar's own deviation from
    # the rolling VWMA (broadcast), which is the standard practical
    # approximation used by these TradingView-style indicators.
    dev_sq = (close - vwma) ** 2
    weighted_dev = (dev_sq * volume).rolling(window).sum() / sum_v
    vw_std = np.sqrt(weighted_dev.clip(lower=0))
    return vwma, vw_std


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 20,
    band_mult: float = 2.0,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    vwma, vw_std = _vwma_and_vwstd(close, volume, window)
    lower_band = vwma - band_mult * vw_std

    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    entry = (close < lower_band) & uptrend.fillna(False)
    exit_meanrev = close > vwma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    entry_vals = entry.fillna(False).values
    exit_vals = exit_meanrev.fillna(False).values

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_vals[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
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

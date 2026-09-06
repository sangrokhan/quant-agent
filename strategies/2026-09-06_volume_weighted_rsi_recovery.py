"""Strategy: Volume-Weighted RSI (VWRSI) oversold-recovery, long-only.

Hypothesis (see knowledge_base id 2026-09-06-151):
Per the TradingView open-source "Volume-Weighted RSI [wbburgin]" script
(https://www.tradingview.com/script/cM6CWwGG-Volume-Weighted-RSI-wbburgin/):
"The Volume-Weighted RSI takes a new approach to the traditional calculation
of the RSI in using a price::volume calculation... built from the square of
the volume change and the price. If the volume decreases rapidly with the
price, the volume-weighted RSI will fall; if the volume increases rapidly
with the price, the volume-weighted RSI will rise." This is a genuinely
different construction from every MFI variant already tested in this repo
(2026-09-04-033, 2026-09-05-011/061, 2026-09-06-129), which weight RSI-style
logic by typical-price*volume dollar flow -- here the *volume's own rate of
change* (squared, to only capture magnitude not direction) scales each bar's
price-based gain/loss before Wilder-style RSI smoothing, so an oversold
signal that occurs on shrinking volume gets discounted (potential
exhaustion, not real selling pressure) while one on expanding volume gets
amplified.

Signal logic
------------
- Daily price change and daily volume % change are both computed.
- Each bar's up/down "gain"/"loss" (standard RSI convention, price-change
  sign) is scaled by (1 + volume_pct_change^2) -- amplifying bars where
  volume moved sharply (in either direction) relative to the prior bar,
  consistent with the source's stated "square of the volume change" scaling
  factor -- then smoothed via Wilder's method (same recursive EMA as
  classic RSI) to get VWRSI(0-100).
- Long entry: VWRSI crosses from <= oversold_threshold up above it
  (oversold-recovery, same convention as every other oscillator-recovery
  strategy in this repo e.g. IMI 2026-09-05-071), gated by close >
  SMA(trend_window) (uptrend filter).
- Exit: VWRSI reaches overbought_threshold, falls back below
  oversold_threshold (failed bounce), trend filter breaks, or a
  max_hold_days time-stop.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _vwrsi(close: pd.Series, volume: pd.Series, window: int = 14) -> pd.Series:
    price_change = close.diff()
    vol_pct_change = volume.pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
    vol_weight = 1.0 + vol_pct_change ** 2

    gain = price_change.clip(lower=0) * vol_weight
    loss = (-price_change.clip(upper=0)) * vol_weight

    # Wilder's smoothing (same recursive EMA convention as classic RSI).
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    vwrsi = 100 - (100 / (1 + rs))
    vwrsi = vwrsi.fillna(50.0)  # neutral where avg_loss is 0 (no losses in window)
    return vwrsi


def generate_signals(
    price_df: pd.DataFrame,
    vwrsi_window: int = 14,
    oversold_threshold: float = 30.0,
    overbought_threshold: float = 70.0,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]
    n = len(close)

    vwrsi = _vwrsi(close, volume, window=vwrsi_window)
    sma = close.rolling(trend_window).mean()
    uptrend = close > sma

    prev_vwrsi = vwrsi.shift(1)
    recovery_entry = (
        (prev_vwrsi <= oversold_threshold)
        & (vwrsi > oversold_threshold)
        & uptrend.fillna(False)
    )

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            exit_ob = vwrsi.iloc[i] >= overbought_threshold
            exit_failed = vwrsi.iloc[i] < oversold_threshold
            exit_trend = not bool(uptrend.iloc[i]) if not pd.isna(uptrend.iloc[i]) else False
            if exit_ob or exit_failed or exit_trend or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(recovery_entry.iloc[i]):
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

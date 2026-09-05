"""Strategy: Trend Intensity Index (TII) extreme-threshold cross (80) with
SMA(50) trend filter, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-080):
Per PineScriptForge's "SB Trend Intensity Index Backtest" strategy
breakdown (Google search snippet): "Enter long when TII crosses above 80
with price above 50 SMA; Enter short when TII..." -- a direct fix attempt
for this repo's already-rejected plain TII midline(50)-cross strategy
(2026-09-04-123, decisive Sharpe/TC-survival fail on QQQ+SPY, too many
low-conviction crossings near the noisy 50 midline). This variant differs
in two ways from 2026-09-04-123: (1) uses an EXTREME threshold (80, "how
strongly price is leaning above its own moving average" per multiple
sources -- TII>80 signals a strong, not just marginal, uptrend) instead of
the noisy 50 midline, and (2) adds an explicit SMA(50) price trend filter
as a second confirming condition, which the plain midline variant lacked
entirely.

Signal logic
------------
- TII (M.H. Pee, 2002): major_sma = SMA(major_period, close); over the
  trailing minor_period window, SDPOS = sum of positive deviations
  (close > major_sma), SDNEG = sum of |negative deviations| (close <
  major_sma); TII = 100 * SDPOS / (SDPOS + SDNEG).
- Entry (long): TII crosses from <= entry_threshold (80) to > entry_threshold
  AND close > SMA(trend_window) (50) at that bar.
- Exit: TII crosses back below exit_threshold (50, reverting toward
  neutral), OR the trend filter breaks (close <= SMA(trend_window)), OR a
  max_hold_days time-stop.
- Flat otherwise.

Interface contract (RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _tii(close: pd.Series, major_period: int, minor_period: int) -> pd.Series:
    major_sma = close.rolling(major_period).mean()
    deviation = close - major_sma

    pos_dev = deviation.where(deviation > 0, 0.0)
    neg_dev = (-deviation).where(deviation < 0, 0.0)

    sdpos = pos_dev.rolling(minor_period).sum()
    sdneg = neg_dev.rolling(minor_period).sum()

    tii = 100.0 * sdpos / (sdpos + sdneg).replace(0.0, np.nan)
    return tii.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    major_period: int = 60,
    minor_period: int = 30,
    trend_window: int = 50,
    entry_threshold: float = 80.0,
    exit_threshold: float = 50.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    tii = _tii(close, major_period, minor_period)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    entry_cross = (tii > entry_threshold) & (tii.shift(1) <= entry_threshold)
    entry = entry_cross.fillna(False) & uptrend.fillna(False)

    exit_cross = (tii < exit_threshold) & (tii.shift(1) >= exit_threshold)
    exit_trend_break = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    entry_vals = entry.to_numpy()
    exit_cross_vals = exit_cross.fillna(False).to_numpy()
    exit_trend_vals = exit_trend_break.to_numpy()

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross_vals[i]) or bool(exit_trend_vals[i]) or held >= max_hold_days:
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

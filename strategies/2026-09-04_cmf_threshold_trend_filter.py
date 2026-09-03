"""Strategy: Chaikin Money Flow (CMF) threshold-cross, SMA-trend-filtered.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-043):
Per a Google AI-overview synthesis (Enlightened Stock Trading / TrendSpider
/ StockCharts ChartSchool sources): Chaikin Money Flow (CMF, Marc Chaikin),
a volume-weighted accumulation/distribution oscillator computed over a
20-21 period lookback, crossing above a small positive threshold (+0.05,
not just zero, to filter weak/noisy zero-line crosses) signals genuine
buying pressure worth trading, distinct from OBV's simpler cumulative
+/-volume construction already tested in this repo (2026-09-04-027,
accepted for QQQ). CMF weights each bar's volume by where the close falls
within that bar's high-low range (Money Flow Multiplier), not just the
sign of the daily close change.

CMF formula (standard, window periods):
    MFM (Money Flow Multiplier) = ((close - low) - (high - close)) / (high - low)
    MFV (Money Flow Volume) = MFM * volume
    CMF = sum(MFV, window) / sum(volume, window)

Signal logic
------------
- Entry (long): CMF crosses above `cmf_threshold` (fresh cross, not every
  bar CMF stays above) AND close > SMA(trend_window) (regime filter).
- Exit: CMF crosses back below zero (source's stated exit rule for long
  trades).
- Flat otherwise; long-only, no shorting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cmf(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]

    range_ = (high - low).replace(0, pd.NA)
    mfm = ((close - low) - (high - close)) / range_
    mfm = mfm.fillna(0.0)
    mfv = mfm * volume

    cmf = mfv.rolling(window).sum() / volume.rolling(window).sum()
    return cmf


def generate_signals(
    price_df: pd.DataFrame,
    cmf_window: int = 20,
    cmf_threshold: float = 0.05,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cmf = _cmf(df, cmf_window)
    sma_trend = close.rolling(trend_window).mean()

    bullish_cross = (cmf > cmf_threshold) & (cmf.shift(1) <= cmf_threshold)
    bearish_cross = (cmf < 0) & (cmf.shift(1) >= 0)

    trend_ok = (close > sma_trend).fillna(False)
    entry = bullish_cross.fillna(False) & trend_ok

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(bearish_cross.iloc[i]) or not bool(trend_ok.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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

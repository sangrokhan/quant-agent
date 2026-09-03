"""Strategy: Accumulation/Distribution (A/D) Line rising-slope trend
confirmation, SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-047):
Per TradingBrokers.com's Accumulation/Distribution guide (Marc Chaikin,
1980s): the A/D Line -- a cumulative running total of each bar's Money
Flow Multiplier (intrabar close position within the high-low range) times
volume -- rising while price is above a moving average confirms uptrend
strength. This is a hybrid construction: CMF's (2026-09-04-043, accepted
QQQ) intrabar-position volume weighting, combined with OBV's (2026-09-04-
027, accepted QQQ) cumulative-running-total structure, rather than either
of those two already-tested constructions individually.

A/D Line formula (standard, cumulative, no fixed window):
    MFM (Money Flow Multiplier) = ((close - low) - (high - close)) / (high - low)
    MFV (Money Flow Volume) = MFM * volume
    A/D = cumulative sum of MFV over the entire series

Signal logic
------------
- "Rising" A/D line: A/D's own `slope_window`-period SMA is trending up
  (A/D SMA > A/D SMA shifted `slope_window` periods ago), a smoothed
  slope proxy avoiding single-bar noise.
- Entry (long): A/D line rising AND close > SMA(trend_window).
- Exit: A/D line no longer rising, OR trend filter breaks.
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


def _ad_line(df: pd.DataFrame) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]

    range_ = (high - low).replace(0, pd.NA)
    mfm = ((close - low) - (high - close)) / range_
    mfm = mfm.fillna(0.0)
    mfv = mfm * volume
    return mfv.cumsum()


def generate_signals(
    price_df: pd.DataFrame,
    slope_window: int = 10,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ad = _ad_line(df)
    ad_smooth = ad.rolling(slope_window).mean()
    ad_rising = ad_smooth > ad_smooth.shift(slope_window)

    sma_trend = close.rolling(trend_window).mean()
    trend_ok = (close > sma_trend).fillna(False)

    entry = ad_rising.fillna(False) & trend_ok
    stay = ad_rising.fillna(False) & trend_ok

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if not bool(stay.iloc[i]):
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

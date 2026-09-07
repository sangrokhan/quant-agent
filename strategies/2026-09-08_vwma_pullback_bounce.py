"""Strategy: VWMA pullback-bounce trend continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-070):
Per TradingWithRayner's "Volume Weighted Moving Average Strategy Guide"
and TrendSpider's VWMA explainer: a SINGLE Volume Weighted Moving Average
(VWMA) can act as dynamic, volume-backed support during an established
uptrend -- "if a stock is trading above VWMA and approaches it during a
pullback, a bounce off VWMA could signal a continuation of the trend."
Concretely: (1) the VWMA(vwma_window) must be clearly sloping upward
(source's own stated setup condition, confirmed here via a positive slope
over slope_lookback bars) with price above a longer-term SMA(trend_window)
trend filter; (2) price pulls back to WITHIN pullback_tolerance of the
VWMA (a "touch" of the dynamic support); (3) entry on the next bar's close
reacting back above the VWMA (the "bounce" confirmation). Exit on close
breaking decisively below the VWMA (support failure), the trend filter
breaking, or a max_hold_days time-stop.

This is mechanically distinct from the already-tested dual-VWMA
CROSSOVER strategy (2026-09-04-060, accepted QQQ/SPY -- uses TWO VWMAs of
different periods crossing each other) -- this strategy uses a SINGLE
VWMA as a pullback/support level for a mean-reversion-within-trend entry,
the same "pullback to a single moving-average line, gated by an uptrend
and a slope condition" pattern already validated for SMA/EMA/HMA lines
elsewhere in this repo, but never yet tested using the VOLUME-WEIGHTED
variant specifically.

Source: https://www.tradingwithrayner.com/volume-weighted-moving-average-strategy/

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
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


def _vwma(df: pd.DataFrame, window: int) -> pd.Series:
    close = df["close"]
    if "volume" in df.columns:
        volume = df["volume"]
    else:
        volume = pd.Series(1.0, index=close.index)
    pv = (close * volume).rolling(window).sum()
    v = volume.rolling(window).sum()
    return pv / v.replace(0, np.nan)


def generate_signals(
    price_df: pd.DataFrame,
    vwma_window: int = 20,
    trend_window: int = 100,
    slope_lookback: int = 5,
    pullback_tolerance: float = 0.01,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    vwma = _vwma(df, vwma_window)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False)
    vwma_rising = (vwma > vwma.shift(slope_lookback)).fillna(False)

    near_vwma = ((close - vwma).abs() / vwma.replace(0, np.nan) <= pullback_tolerance).fillna(False)
    was_above_vwma_recently = (close.shift(1) > vwma.shift(1)).fillna(False)

    entry_setup = uptrend & vwma_rising & near_vwma & was_above_vwma_recently
    bounce_confirm = close > vwma

    entry = (entry_setup & bounce_confirm).fillna(False)
    exit_break = (close < vwma).fillna(False)

    entry_arr = entry.to_numpy(dtype=bool)
    exit_arr = exit_break.to_numpy(dtype=bool)
    uptrend_arr = uptrend.to_numpy(dtype=bool)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_arr[i]) or (not bool(uptrend_arr[i])) or held >= max_hold_days:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if bool(entry_arr[i]):
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
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret

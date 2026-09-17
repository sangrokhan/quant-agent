"""Strategy: Apirine Stochastic Distance Oscillator (SDO) oversold-recovery.

Source: TASC (Technical Analysis of Stocks & Commodities) June 2023,
Vitali Apirine, "The Stochastic Distance Oscillator", via
https://traders.com/Documentation/FEEDbk_docs/2023/06/TradersTips.html
(visited this iteration, see knowledge_base/visited_pages.jsonl), fully
disclosed TradeStation EasyLanguage:

    Dist = |Close - Close[Period]|                       # N-bar move magnitude
    DVal = (Dist - Lowest(Dist, Period))
           / (Highest(Dist, LBPeriod) - Lowest(Dist, LBPeriod))
    DDVal = +DVal if Close > Close[Period]                # signed by direction
            -DVal if Close < Close[Period]
            0 otherwise
    SDO = EMA(DDVal, Pds) * 100

Default: LBPeriod=200, Period=12, Pds=3, OverBought=40, OverSold=-40.

The SDO normalizes the magnitude of an N-bar price move (Dist) against a
LONG lookback range (its own min/max distance over the trailing LBPeriod
bars, default 200), then signs it by direction and EMA-smooths. This is
distinct from the classic Stochastic oscillator (normalizes CLOSE against
the trailing HIGH/LOW price range, not a distance-of-move statistic) and
from every other Apirine oscillator already tested in this repo (ROCWB
uses RMS-based bands, STMACD uses stochastic-normalized EMA spread, HHLLS
uses fresh-extreme-ratio EMAs) -- first SDO-specific strategy in this repo.

Trading rule (source's own disclosed default overbought/oversold levels,
+40/-40, this repo's standard oversold-recovery crossover treatment):
long entry when SDO crosses up through `oversold` from below, gated by
`close > SMA(trend_window)`; exit when SDO crosses back down through
`overbought`, or a `max_hold_days` time-stop.

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _sdo(close: pd.Series, lb_period: int, period: int, pds: int) -> pd.Series:
    dist = (close - close.shift(period)).abs()
    dist_low = dist.rolling(period).min()
    dist_range_hi = dist.rolling(lb_period).max()
    dist_range_lo = dist.rolling(lb_period).min()
    denom = (dist_range_hi - dist_range_lo).replace(0.0, np.nan)
    dval = (dist - dist_low) / denom

    direction = np.sign(close - close.shift(period))
    ddval = (dval * direction).fillna(0.0)

    sdo = ddval.ewm(span=pds, adjust=False).mean() * 100.0
    return sdo


def generate_signals(
    price_df: pd.DataFrame,
    lb_period: int = 200,
    period: int = 12,
    pds: int = 3,
    oversold: float = -15.0,
    overbought: float = 20.0,
    trend_window: int = 150,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sdo = _sdo(close, lb_period, period, pds)
    trend_sma = close.rolling(trend_window).mean()

    cross_up = (sdo > oversold) & (sdo.shift(1) <= oversold)
    cross_down = (sdo < overbought) & (sdo.shift(1) >= overbought)
    trend_ok = close > trend_sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]) and bool(trend_ok.iloc[i]):
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

"""Strategy: Apirine Linear Regression-Adjusted EMA (LRAdj EMA) vs EMA crossover.

Source: TASC (Technical Analysis of Stocks & Commodities) September 2022
Traders' Tips (implementing the August 2022 article), Vitali Apirine, "The
Linear Regression-Adjusted Exponential Moving Average", via
https://traders.com/Documentation/FEEDbk_docs/2022/09/TradersTips.html
(visited this iteration, see knowledge_base/visited_pages.jsonl), fully
disclosed TradeStation EasyLanguage series function:

    Mltp1 = 2 / (Periods + 1)
    LR    = LinearRegValue(Close, Pds, 0)     # linear regression value at bar 0
    Dist  = |LR - Close|
    ST    = (Dist - Lowest(Dist, Pds)) / (Highest(Dist, Pds) - Lowest(Dist, Pds))
    Mltp2 = ST * Mltp
    Rate  = Mltp1 * (1 + Mltp2)
    LRAdjEMA[t] = LRAdjEMA[t-1] + Rate * (Close - LRAdjEMA[t-1])

LRAdj EMA is a price-based adaptive-rate EMA whose adaptive component (ST)
measures how far price currently sits from its own rolling linear-regression
trendline (min-max normalized over the same lookback), speeding up when
price deviates strongly from trend and slowing down when price tracks the
trendline closely. This is a DISTINCT adaptive-rate mechanism from every
other adaptive-EMA family already tested in this repo: RS EMA (own up/down
day EMA asymmetry, id 2026-09-17-164), Relative VIX Strength EMA (VIX
asymmetry, rejected 2026-09-12-184), and TRAdj EMA (True-Range-based, ids
2026-09-12-196/197) -- LRAdj EMA is the first adaptive-rate construction in
this repo driven by deviation-from-a-fitted-trendline rather than a
volatility or momentum-asymmetry ratio.

Trading rule (source's own suggested use, "The LRAdj EMA can be used in
combination with a traditional exponential moving average of the same
length to facilitate trend identification", explicitly demoed by the
Wealth-Lab Traders' Tip contributor as a crossover system against a
long-term (200-period) EMA): long when LRAdj EMA crosses above a plain
EMA of the same `periods` length; exit on the reverse cross (with a
`min_hold_days` hysteresis, this repo's standard whipsaw-reduction pattern)
or a `max_hold_days` time-stop.

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


def _linreg_value(close: pd.Series, pds: int) -> pd.Series:
    """Rolling linear-regression fitted value at the current (last) bar of
    each `pds`-length window (TradeStation's LinearRegValue(Close, Pds, 0))."""
    x = np.arange(pds)
    x_mean = x.mean()
    denom = ((x - x_mean) ** 2).sum()

    def _fit_last(window: np.ndarray) -> float:
        y_mean = window.mean()
        slope = ((x - x_mean) * (window - y_mean)).sum() / denom
        intercept = y_mean - slope * x_mean
        return intercept + slope * (pds - 1)

    return close.rolling(pds).apply(_fit_last, raw=True)


def _lradj_ema(close: pd.Series, periods: int, pds: int, mltp: float) -> pd.Series:
    mltp1 = 2.0 / (periods + 1)
    lr = _linreg_value(close, pds)
    dist = (lr - close).abs()
    dist_min = dist.rolling(pds).min()
    dist_max = dist.rolling(pds).max()
    denom = (dist_max - dist_min).replace(0.0, np.nan)
    st = ((dist - dist_min) / denom).fillna(0.0).clip(0.0, 1.0)
    mltp2 = st * mltp
    rate = (mltp1 * (1.0 + mltp2)).clip(upper=1.0)

    lradj = pd.Series(index=close.index, dtype=float)
    prev = None
    for i, (r, c) in enumerate(zip(rate.to_numpy(), close.to_numpy())):
        if prev is None or pd.isna(prev):
            prev = c
        else:
            prev = prev + r * (c - prev)
        lradj.iloc[i] = prev
    return lradj


def generate_signals(
    price_df: pd.DataFrame,
    periods: int = 30,
    pds: int = 30,
    mltp: float = 4.0,
    min_hold_days: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when LRAdj EMA crosses above a plain EMA of the same `periods`
    length (source's own suggested crossover pairing); exit on reverse
    cross (after `min_hold_days` hysteresis) or `max_hold_days` time-stop.
    """
    df = _prep(price_df)
    close = df["close"]

    lradj = _lradj_ema(close, periods, pds, mltp)
    plain_ema = close.ewm(span=periods, adjust=False).mean()

    bullish = lradj > plain_ema

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            want_flat = (not bool(bullish.iloc[i])) and held >= min_hold_days
            if want_flat or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(bullish.iloc[i]):
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

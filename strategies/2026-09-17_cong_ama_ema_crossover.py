"""Strategy: Scott Cong's Adaptive Moving Average (AMA) vs EMA crossover.

Source: TASC (Technical Analysis of Stocks & Commodities) May 2023 Traders'
Tips (implementing the March 2023 article), Scott Cong, "An Adaptive
Moving Average For Swing Trading", via
https://traders.com/Documentation/FEEDbk_docs/2023/05/TradersTips.html
(visited this iteration, see knowledge_base/visited_pages.jsonl), fully
disclosed TradeStation EasyLanguage function:

    HH = Highest(High, Length)
    LL = Lowest(Low, Length)
    Result = HH - LL
    Effort = Summation(TrueRange, Length)
    AlphaValue = Result / Effort   (clamped to 1 if Effort == 0)
    AMA[t] = AlphaValue * Price + (1 - AlphaValue) * AMA[t-1]

Cong's AMA is an adaptive-EMA whose alpha (smoothing weight) is a "range
efficiency ratio": the NET high-low range of the lookback window divided
by the CUMULATIVE true range (sum of each bar's own true range) over the
same window. When price makes clean, single-directional progress (net
range close to cumulative true range, little backtracking), alpha -> 1 and
AMA tracks price almost exactly (fast); when price chops back and forth
(net range << cumulative true range), alpha -> 0 and AMA barely moves
(slow). This is DISTINCT from Kaufman's classic KAMA efficiency ratio
(net price CHANGE over sum of absolute price CHANGES, no high/low/true
range) and from the FRAMA fractal-dimension adaptive rate and RS
EMA/LRAdj EMA/TRAdj EMA constructions already tested in this repo -- first
strategy using Cong's specific range-vs-true-range-sum efficiency ratio.

Trading rule (this repo's standard treatment for a bare adaptive-MA
indicator, consistent with RS EMA id=2026-09-17-164 and LRAdj EMA
id=2026-09-17-165): long when Cong's AMA crosses above a plain EMA of the
same `length`, gated by `close > SMA(trend_window)`; exit on the reverse
cross (`min_hold_days` hysteresis) or a `max_hold_days` time-stop.

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


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def _cong_ama(df: pd.DataFrame, length: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    hh = high.rolling(length).max()
    ll = low.rolling(length).min()
    result = hh - ll
    tr = _true_range(high, low, close)
    effort = tr.rolling(length).sum()

    alpha = (result / effort.replace(0.0, np.nan)).fillna(1.0).clip(0.0, 1.0)

    ama = pd.Series(index=close.index, dtype=float)
    prev = None
    for i, (a, p) in enumerate(zip(alpha.to_numpy(), close.to_numpy())):
        if prev is None or pd.isna(prev):
            prev = p
        else:
            if a >= 1.0:
                prev = p
            else:
                prev = a * p + (1.0 - a) * prev
        ama.iloc[i] = prev
    return ama


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 15,
    trend_window: int = 50,
    min_hold_days: int = 10,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ama = _cong_ama(df, length)
    plain_ema = close.ewm(span=length, adjust=False).mean()
    trend_sma = close.rolling(trend_window).mean()

    bullish = (ama > plain_ema) & (close > trend_sma)

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

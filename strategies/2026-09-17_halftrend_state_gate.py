"""Strategy: HalfTrend (indicator by TradingView user "everget") trend-flip
long-only signal.

Hypothesis (grounded in Step 2 research this iteration):
Per the full Pine Script v5 source code found on GitHub
(https://github.com/pradip-interra/PineScripts/blob/main/strategy_ht_ce_pd_rsi_combined.ps,
which explicitly credits "HalfTrend by everget
(https://www.tradingview.com/script/U1SJ8ubc-HalfTrend)"), HalfTrend is a
non-repainting ATR-based trend-flip line: it tracks SMA(high,amplitude) and
SMA(low,amplitude) against the highest-high/lowest-low over the same
`amplitude` window, flips its internal `trend` state from down(1) to up(0)
when `SMA(low,amplitude) > minHighPrice AND close > prior high` (and
symmetrically for the down-flip), then trails an ATR(100)/2-based up/down
line. Source's own disclosed buy/sell rule (from the same Pine code):
`buySignal = trend == 0 and trend[1] == 1` (i.e. exactly on the flip from
downtrend to uptrend) and the symmetric `sellSignal` on the reverse flip.
Implemented long-only: hold position while `trend == 0` (uptrend state),
flat while `trend == 1` (downtrend state) -- this is the source's own
buySignal/sellSignal framed as a continuous regime rather than point
signals, which is the natural translation for a `generate_signals`
0/1-position contract.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
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


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _halftrend_state(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    amplitude: int,
    atr_length: int,
) -> pd.Series:
    """Port of everget's HalfTrend Pine v5 script: returns the `trend`
    state series (0 = uptrend, 1 = downtrend)."""
    n = len(close)
    high_ma = high.rolling(amplitude, min_periods=amplitude).mean().to_numpy()
    low_ma = low.rolling(amplitude, min_periods=amplitude).mean().to_numpy()
    high_price = high.rolling(amplitude, min_periods=amplitude).max().to_numpy()
    low_price = low.rolling(amplitude, min_periods=amplitude).min().to_numpy()
    close_arr = close.to_numpy()
    prev_high = high.shift(1).to_numpy()
    prev_low = low.shift(1).to_numpy()

    trend = np.zeros(n, dtype=int)
    next_trend = np.zeros(n, dtype=int)
    max_low_price = np.full(n, np.nan)
    min_high_price = np.full(n, np.nan)

    start = amplitude
    if start >= n:
        return pd.Series(trend, index=close.index)

    max_low_price[start - 1] = prev_low[start] if not np.isnan(prev_low[start]) else low.iloc[start]
    min_high_price[start - 1] = prev_high[start] if not np.isnan(prev_high[start]) else high.iloc[start]

    for i in range(start, n):
        prev_next_trend = next_trend[i - 1]
        prev_max_low = max_low_price[i - 1]
        prev_min_high = min_high_price[i - 1]

        cur_trend = trend[i - 1]
        cur_next_trend = prev_next_trend
        cur_max_low = prev_max_low
        cur_min_high = prev_min_high

        if prev_next_trend == 1:
            cur_max_low = max(low_price[i], prev_max_low)
            if high_ma[i] < cur_max_low and close_arr[i] < prev_low[i]:
                cur_trend = 1
                cur_next_trend = 0
                cur_min_high = high_price[i]
        else:
            cur_min_high = min(high_price[i], prev_min_high)
            if low_ma[i] > cur_min_high and close_arr[i] > prev_high[i]:
                cur_trend = 0
                cur_next_trend = 1
                cur_max_low = low_price[i]

        trend[i] = cur_trend
        next_trend[i] = cur_next_trend
        max_low_price[i] = cur_max_low
        min_high_price[i] = cur_min_high

    return pd.Series(trend, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    amplitude: int = 2,
    atr_length: int = 100,
) -> pd.Series:
    """Return a 0/1 position series.

    Long while HalfTrend's internal `trend` state is 0 (uptrend, source's
    own state that gates `buySignal`); flat while `trend` is 1
    (downtrend).
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    trend = _halftrend_state(high, low, close, amplitude, atr_length)
    position = (trend == 0).astype(float)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    amplitude: int = 2,
    atr_length: int = 100,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, amplitude=amplitude, atr_length=atr_length)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret

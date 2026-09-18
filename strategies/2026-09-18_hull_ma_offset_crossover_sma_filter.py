"""Strategy: Hull Moving Average Same-Offset Crossover + Long-Term SMA Filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD, source
https://opportrade.com/articles/hull-MA-strategy, "Hull MA Crossover
Strategy With SMA Filter"):

First HMA-family strategy in this repo (0 prior KB hits for "Hull Moving
Average" or "HMA"). The Hull Moving Average (Alan Hull) reduces the lag
typical of SMA/EMA while staying smoother than a raw WMA, via:
    raw_hma(period) = WMA(2*WMA(close, period/2) - WMA(close, period), sqrt(period))

Source's exact disclosed rule (Tradescript, tested by them on ETH/EUR 1h
2025): compute a SINGLE HMA(period=32, half=16, sqrt_period=6) series, then
take TWO DIFFERENT TIME-OFFSET readings of that same series -- H_L1 (1 bar
lag) and H_L4 (4 bars lag) -- and trade the crossover BETWEEN those two
offsets of the same underlying HMA (not two HMAs of different periods).
Long entry: H_L1 crosses above H_L4 (the more-recent reading overtakes the
older one, i.e. the HMA's slope just turned positive/steepened), filtered
by previous close > SMA(500) (long-term uptrend confirmation). Long exit:
H_L4 crosses back below H_L1 (slope decelerating/reversing).

Economic rationale (per source): using two lag-offsets of the SAME
low-lag HMA to detect slope changes is more responsive than a traditional
dual-period (fast HMA/slow HMA) crossover, since both series share
identical smoothing -- only the offset differs -- so the crossover fires
essentially as soon as the HMA's local slope inflects, rather than waiting
for a slower separate average to catch up.

This repo trades daily bars (not 1h ETH/EUR as in the source), so period
parameters are rescaled and grid-tested rather than assumed to transfer
directly (32-bar HMA divided across daily bars represents roughly
1.5 trading months, plausible for a daily-bar trend-following signal;
SMA(500) trend filter kept close to source's SMA(500) since it's already a
roughly 2-year daily-bar lookback which is a standard long-term filter).

Interface contract for validators (see validation/validators.py) and
grid_test.py (Step 6): generate_signals/generate_returns both accept
tunable parameters as keyword arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wma(series: pd.Series, period: int) -> pd.Series:
    weights = pd.Series(range(1, period + 1), dtype=float)

    def _w_avg(x):
        return (x * weights.values).sum() / weights.sum()

    return series.rolling(period).apply(_w_avg, raw=True)


def _hma(close: pd.Series, period: int) -> pd.Series:
    half = max(1, period // 2)
    sqrt_p = max(1, int(round(period ** 0.5)))
    raw = 2 * _wma(close, half) - _wma(close, period)
    return _wma(raw, sqrt_p)


def generate_signals(
    price_df: pd.DataFrame,
    hma_period: int = 32,
    fast_offset: int = 1,
    slow_offset: int = 4,
    trend_sma_window: int = 500,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: HMA(hma_period) shifted by fast_offset crosses above the
    SAME HMA series shifted by slow_offset, filtered by previous close >
    SMA(trend_sma_window). Long exit: the slow-offset reading crosses back
    above the fast-offset reading.
    """
    df = _prep(price_df)
    close = df["close"]

    hma = _hma(close, hma_period)
    h_fast = hma.shift(fast_offset)
    h_slow = hma.shift(slow_offset)

    trend_sma = close.rolling(trend_sma_window, min_periods=trend_sma_window // 2).mean()
    trend_ok = (close.shift(1) > trend_sma.shift(1)).fillna(False)

    cross_up = (h_fast > h_slow) & (h_fast.shift(1) <= h_slow.shift(1))
    cross_down = (h_slow > h_fast) & (h_slow.shift(1) <= h_fast.shift(1))

    entry = cross_up & trend_ok
    exit_ = cross_down

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
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

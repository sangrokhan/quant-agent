"""Strategy: Ehlers Undersampled Double MA (Hann-windowed FIR) crossover.

Source: TASC (Technical Analysis of Stocks & Commodities) April 2023, John
F. Ehlers, "Just Ignore Them: Undersampling The Data As A Smoothing
Technique", via
https://traders.com/Documentation/FEEDbk_docs/2023/04/TradersTips.html
(visited this iteration, see knowledge_base/visited_pages.jsonl), fully
disclosed TradeStation EasyLanguage:

    $Hann(Price, Length):
        Filt = sum_{c=1..Length} (1-cos(360*c/(Length+1))) * Price[c-1]
        Coef = sum_{c=1..Length} (1-cos(360*c/(Length+1)))
        return Filt / Coef

    Sample = Close every 5th bar, else carried forward from the prior
             sampled value (undersampling -- the article's core proposal:
             smoothing on an UNDERSAMPLED series removes high-frequency
             noise with LESS LAG than smoothing every bar of the full-rate
             series).
    FastAvg = $Hann(Sample, FastLength)   # default FastLength=6
    SlowAvg = $Hann(Sample, SlowLength)   # default SlowLength=12

This is a DISTINCT smoothing mechanism from every other Hann-windowed
construction already in this repo (MADH, id=2026-09-12-162, applies the
Hann FIR filter to the FULL-RATE daily series, no undersampling step) --
first undersampling-based strategy in this repo (0 prior KB hits for
"undersampl").

Trading rule (source's own suggested comparison use, consistent with this
repo's treatment of other bare dual-MA Ehlers constructions, e.g. MAD/MADH/
RS EMA/LRAdj EMA all use a fast/slow crossover): long when FastAvg crosses
above SlowAvg, gated by `close > SMA(trend_window)`; exit on the reverse
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


def _undersample(close: pd.Series, sample_every: int) -> pd.Series:
    """Sample close every `sample_every` bars (by integer bar position),
    forward-filling the last sampled value in between (matches the
    source's `if CurrentBar/5 = IntPortion(CurrentBar/5)` construction)."""
    n = len(close)
    idx_arr = np.arange(n)
    is_sample_bar = (idx_arr % sample_every) == 0
    sampled = close.where(pd.Series(is_sample_bar, index=close.index))
    return sampled.ffill().bfill()


def _hann_fir(sample: pd.Series, length: int) -> pd.Series:
    counts = np.arange(1, length + 1)
    weights = 1.0 - np.cos(2.0 * np.pi * counts / (length + 1))
    coef_sum = weights.sum()

    values = sample.to_numpy()
    n = len(values)
    out = np.full(n, np.nan)
    for i in range(length, n):
        window = values[i - length : i]  # Price[count-1] for count=1..Length -> most recent `length` bars before i
        out[i] = np.dot(weights, window[::-1]) / coef_sum
    return pd.Series(out, index=sample.index)


def generate_signals(
    price_df: pd.DataFrame,
    sample_every: int = 5,
    fast_length: int = 6,
    slow_length: int = 25,
    trend_window: int = 100,
    min_hold_days: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sample = _undersample(close, sample_every)
    fast_avg = _hann_fir(sample, fast_length)
    slow_avg = _hann_fir(sample, slow_length)
    trend_sma = close.rolling(trend_window).mean()

    bullish = (fast_avg > slow_avg) & (close > trend_sma)

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

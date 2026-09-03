"""Strategy: Hull Moving Average (HMA) single-line crossover trend-follow.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-026):
Per CoinQuant's BTC/USDT HMA strategy page
(https://www.coinquant.ai/strategies/btc-hma-5m-backtest): a single Hull
Moving Average (HMA), which uses a reduced-lag weighted-moving-average
formula, crossed by price signals a momentum shift -- long when close
crosses above HMA(hma_window), exit when close crosses back below. The
source's OWN backtest is decisively negative at 5-minute BTC/USDT
frequency (ROI -99.91%, Sharpe -8.21) due to whipsaw in choppy conditions
at that high frequency; this iteration deliberately tests the same simple
crossover rule at DAILY bar frequency (a frequency mismatch vs the
source, similar in spirit to -023's noted future-work idea) on both
equity and crypto to see if the mechanism transfers better at a lower,
less noisy sampling rate. First Hull Moving Average (reduced-lag weighted
smoothing) construction tested in this repo -- distinct from SMA/EMA
crossovers (golden-cross 2026-09-03-021, MACD 2026-09-03-013).

Signal logic
------------
- HMA(hma_window) = WMA(2*WMA(close, hma_window//2) - WMA(close, hma_window),
  round(sqrt(hma_window))) -- the standard Hull formula.
- Entry (long): close crosses from <= HMA to > HMA (fresh crossover above).
- Exit: close crosses from > HMA to <= HMA (fresh crossover below).
- Flat otherwise; long-only, no shorting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = pd.Series(range(1, window + 1), dtype=float)
    return series.rolling(window).apply(
        lambda x: (x * weights.values).sum() / weights.sum(), raw=True
    )


def _hma(close: pd.Series, hma_window: int) -> pd.Series:
    half_window = max(1, hma_window // 2)
    sqrt_window = max(1, round(math.sqrt(hma_window)))
    wma_half = _wma(close, half_window)
    wma_full = _wma(close, hma_window)
    raw_hma = 2 * wma_half - wma_full
    return _wma(raw_hma, sqrt_window)


def generate_signals(
    price_df: pd.DataFrame,
    hma_window: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    hma = _hma(close, hma_window)

    above = close > hma
    entry = above & (~above.shift(1).fillna(False))
    exit_cross = (~above) & (above.shift(1).fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_cross.iloc[i]):
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

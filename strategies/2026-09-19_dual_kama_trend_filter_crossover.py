"""Strategy: Dual Kaufman Adaptive Moving Average (KAMA) trend-filter + crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-055):
Per StockCharts.com's "Kaufman's Adaptive Moving Average (KAMA)" explainer
(https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/kaufmans-adaptive-moving-average-kama),
KAMA (developed by Perry Kaufman) adapts its smoothing speed to market
noise via an Efficiency Ratio (ER, price change over N periods divided by
the sum of absolute period-to-period changes -- 1.0 in a clean trend, ~0
in chop), tracking price closely in clean trends and slowing down in
choppy/noisy conditions -- addressing the well-known whipsaw problem of
fixed-period SMA/EMA crossovers in sideways markets. StockCharts'
own disclosed technique: use a longer-term, more-smoothed KAMA (slower
fastest-EMA-constant, e.g. KAMA(er_window,5,30)) as a trend filter
(bullish regime when this KAMA is rising), then take bullish price-crosses
above a faster/more-responsive KAMA (KAMA(er_window,2,30)) only while the
trend-filter KAMA confirms the regime. This is the first KAMA-based
strategy in this repo (novelty index search returned zero prior KAMA
entries) -- a genuinely different adaptive-smoothing mechanism from every
other moving-average variant already tested (Hull MA, T3, Guppy Multiple
MA, FRAMA/Ehlers-family adaptive filters).

Signal logic
------------
- Efficiency Ratio: ER = |close - close.shift(er_window)| / sum(|close.diff()|
  over the trailing er_window periods).
- Smoothing Constant: SC = (ER * (fast_sc - slow_sc) + slow_sc) ** 2, where
  fast_sc = 2/(fast_ema+1), slow_sc = 2/(slow_ema+1).
- KAMA[t] = KAMA[t-1] + SC[t] * (close[t] - KAMA[t-1]), seeded with the
  first available close.
- Compute kama_fast = KAMA(er_window, fast_ema=2, slow_ema=30) and
  kama_trend = KAMA(er_window, fast_ema=5, slow_ema=30) (StockCharts'
  disclosed dual-KAMA construction).
- trend_bullish = kama_trend.diff() > 0 (rising trend-filter KAMA).
- Entry/hold (long): close > kama_fast AND trend_bullish.
- Exit: either condition breaks (flat).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _kama(close: pd.Series, er_window: int, fast_ema: int, slow_ema: int) -> pd.Series:
    """Kaufman's Adaptive Moving Average."""
    change = (close - close.shift(er_window)).abs()
    volatility = close.diff().abs().rolling(er_window).sum()
    er = (change / volatility.replace(0, np.nan)).fillna(0.0)

    fast_sc = 2.0 / (fast_ema + 1)
    slow_sc = 2.0 / (slow_ema + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    kama = pd.Series(index=close.index, dtype=float)
    first_valid = close.first_valid_index()
    if first_valid is None:
        return kama

    values = close.to_numpy(dtype=float)
    sc_values = sc.to_numpy(dtype=float)
    kama_values = np.full(len(values), np.nan, dtype=float)
    start_pos = close.index.get_loc(first_valid)
    kama_values[start_pos] = values[start_pos]

    for i in range(start_pos + 1, len(values)):
        prev = kama_values[i - 1]
        if np.isnan(prev):
            kama_values[i] = values[i]
        else:
            kama_values[i] = prev + sc_values[i] * (values[i] - prev)
    return pd.Series(kama_values, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    er_window: int = 10,
    fast_ema: int = 2,
    slow_ema: int = 30,
    trend_fast_ema: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    kama_fast = _kama(close, er_window, fast_ema, slow_ema)
    kama_trend = _kama(close, er_window, trend_fast_ema, slow_ema)

    trend_bullish = (kama_trend.diff() > 0).fillna(False)
    price_above_fast = (close > kama_fast).fillna(False)

    position = (price_above_fast & trend_bullish).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    er_window: int = 10,
    fast_ema: int = 2,
    slow_ema: int = 30,
    trend_fast_ema: int = 5,
) -> pd.Series:
    """Return the strategy's daily return series."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        er_window=er_window,
        fast_ema=fast_ema,
        slow_ema=slow_ema,
        trend_fast_ema=trend_fast_ema,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

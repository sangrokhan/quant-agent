"""Strategy: Ehlers Predictive Moving Average (PMA) predict/trigger crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-061):
Per John Ehlers' "Predictive Moving Average" (Rocket Science for Traders,
2001, ch.20; explainer at
https://vectoralpha.dev/projects/ta/indicators/ehlers_pma/), a
double-smoothed WMA extrapolation reduces lag beyond a traditional moving
average: WMA1 = 7-period WMA of price; WMA2 = 7-period WMA of WMA1
(double-smoothed); predict = 2*WMA1 - WMA2 (linear extrapolation assuming
the current trend in the WMA continues); trigger = 4-period WMA of
predict (a smoother companion line). Ehlers' own fixed defaults
(WMA lengths 7, 7, 4) were "optimized through extensive testing,
eliminating the need for user adjustment." Trading rule: bullish cross
(predict crosses above trigger) signals long, bearish cross signals
short/flat.

This is a DIFFERENT PMA from the already-tested "Ehlers Projected Moving
Average" (2026-09-13-024/025, rejected: SMA + linear-regression-slope
projection, PMA=SMA+slope*Length/2, from TASC March 2025 "Removing Moving
Average Lag") -- an unfortunate acronym collision between two genuinely
distinct Ehlers constructions from different sources/years. This
Predictive Moving Average uses DOUBLE-WMA EXTRAPOLATION (2*WMA1-WMA2),
not a slope-based linear-regression projection. First strategy in this
repo using this specific WMA-extrapolation predict/trigger construction.

We adapt the source's raw predict/trigger crossover into a {0,1}
long/flat contract (rather than long/short) gated by a longer-term SMA
trend filter -- the same defensive pattern already validated for other
crossover-prone Ehlers/adaptive-MA constructions in this repo (KAMA,
LSMA, Hull MA), since Ehlers' own source notes the indicator "works
particularly well in trending markets" and recommends combining with a
trend/volatility filter to avoid whipsaws during choppy conditions.

Signal logic
------------
- wma1 = WMA(close, wma1_len) [default 7].
- wma2 = WMA(wma1, wma2_len) [default 7].
- predict = 2*wma1 - wma2.
- trigger = WMA(predict, trigger_len) [default 4].
- bullish_cross = predict > trigger.
- trend_up = close > SMA(close, trend_window).
- Long (position=1) when bullish_cross AND trend_up; flat otherwise.

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


def _wma(series: pd.Series, window: int) -> pd.Series:
    """Weighted moving average (linearly increasing weights, most recent bar heaviest)."""
    weights = np.arange(1, window + 1, dtype=float)
    return series.rolling(window).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    wma1_len: int = 14,
    wma2_len: int = 5,
    trigger_len: int = 4,
    trend_window: int = 150,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    wma1 = _wma(close, wma1_len)
    wma2 = _wma(wma1, wma2_len)
    predict = 2 * wma1 - wma2
    trigger = _wma(predict, trigger_len)

    bullish_cross = (predict > trigger).fillna(False)
    sma = close.rolling(trend_window).mean()
    trend_up = (close > sma).fillna(False)

    position = (bullish_cross & trend_up).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    wma1_len: int = 14,
    wma2_len: int = 5,
    trigger_len: int = 4,
    trend_window: int = 150,
) -> pd.Series:
    """Return the strategy's daily return series."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        wma1_len=wma1_len,
        wma2_len=wma2_len,
        trigger_len=trigger_len,
        trend_window=trend_window,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

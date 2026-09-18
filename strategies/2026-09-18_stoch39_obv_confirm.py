"""Strategy: 39-period Slow Stochastic %K 50-line cross, OBV-confirmed
(StockCharts "The Last Stochastic Technique").

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
Per StockCharts.com ChartSchool's "The 'Last' Stochastic Technique"
(https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/the-last-stochastic-technique,
read via browser_exec fallback after web_search's DDGS backend could not
extract page content, citing "The Encyclopedia of Technical Market
Indicators"): a LONG-PERIOD (39-bar, vs. the classic 14-bar) Stochastic
Oscillator %K crossing above its own 50 midline, when confirmed by an
independent volume-based indicator (On-Balance Volume above its own 30-day
SMA), produces a higher-quality trend-continuation signal than either
indicator alone -- avoiding many of the whipsaws that plague short-period
overbought/oversold Stochastic signals. Long entry requires the joint
condition (both %K>50 AND OBV>OBV's own 30-day SMA); exit when either
condition reverses (source's own worked example: "%K moved below 50... this
move was confirmed as OBV moved below its 30-day SMA... no signal [on a
later %K cross] because the price momentum signal was not confirmed by
OBV").

This is distinct from the already-tested plain Stochastic 50-line
continuation strategies in this repo (2026-09-04-163's %K>50 + SMA trend
filter, no OBV; 2026-09-09-084 confirmed as duplicate research) because: (a)
it uses the source's specific 39-period UNSMOOTHED %K (vs. the classic
14-period), and (b) the confirming filter is an independent VOLUME
indicator (OBV vs its own SMA) rather than a price-trend SMA filter --
requiring both momentum AND volume-flow agreement, a genuinely different
two-indicator joint-condition construction never tested in this repo's
existing Stochastic-family entries.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
    generate_returns(price_df, **params) -> pd.Series
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


def _stochastic_k(df: pd.DataFrame, window: int) -> pd.Series:
    low_min = df["low"].rolling(window).min()
    high_max = df["high"].rolling(window).max()
    denom = (high_max - low_min).replace(0, np.nan)
    k = 100.0 * (df["close"] - low_min) / denom
    return k.fillna(50.0)


def _obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df["close"].diff().fillna(0.0))
    return (direction * df["volume"]).cumsum()


def _core(
    price_df: pd.DataFrame,
    stoch_window: int = 39,
    obv_sma_window: int = 30,
    k_midline: float = 50.0,
) -> pd.Series:
    df = _prep(price_df)
    k = _stochastic_k(df, stoch_window)
    obv = _obv(df)
    obv_sma = obv.rolling(obv_sma_window).mean()

    bullish_momentum = k > k_midline
    bullish_volume = obv > obv_sma
    position = (bullish_momentum & bullish_volume).astype(int)
    return position


def generate_signals(
    price_df: pd.DataFrame,
    stoch_window: int = 39,
    obv_sma_window: int = 30,
    k_midline: float = 50.0,
) -> pd.Series:
    return _core(price_df, stoch_window, obv_sma_window, k_midline)


def generate_returns(
    price_df: pd.DataFrame,
    stoch_window: int = 39,
    obv_sma_window: int = 30,
    k_midline: float = 50.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = _core(df, stoch_window, obv_sma_window, k_midline)
    daily_ret = close.pct_change().fillna(0.0)
    return daily_ret * position.shift(1).fillna(0)

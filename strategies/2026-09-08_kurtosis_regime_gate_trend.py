"""Strategy: rolling excess-kurtosis regime gate on an SMA trend-following signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-180):
Per Federico Carrone's "Leptokurtic" series, Episode 2 "Detecting Crashes
with Fat-Tail Statistics" (https://federicocarrone.com/series/leptokurtic),
financial return distributions are leptokurtic (fat-tailed) rather than
Gaussian, and elevated fat-tailedness/kurtosis in returns has been used as
one of several crash-detection signals (alongside LPPLS, DFA, EVT, Hurst,
etc., tested against 96 historical drawdowns across BTC/SPY/Gold/forex in
the source's own fatcrash toolkit). The general thesis: periods of unusually
high rolling excess kurtosis in daily returns (fatter tails than the
asset's own recent baseline) signal elevated crash/tail-risk, during which
a trend-following strategy should reduce or exit exposure.

Implementation: compute rolling excess kurtosis (Fisher definition, i.e.
0 = normal distribution) of daily log returns over `kurtosis_window` days,
compare it to its own trailing `lookback` days of history via percentile
rank (no external asset/dataset needed, consistent with this repo's
single-symbol data/loaders.py constraint). Long only when in an SMA
uptrend AND the kurtosis percentile rank is BELOW `kurtosis_pct_threshold`
(i.e. NOT in an unusually fat-tailed/crash-risk regime); flat otherwise.

First kurtosis-based regime-gate entry in this repo -- mechanically
distinct from the realized-volatility-percentile gate used elsewhere
(volatility measures dispersion magnitude; kurtosis measures the SHAPE of
the return distribution's tails independent of overall dispersion level)
and from realized-skewness gates (2026-09-08-055/154, which measure
distributional asymmetry, not tail thickness).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    kurtosis_window: int = 20,
    lookback: int = 252,
    kurtosis_pct_threshold: float = 0.8,
) -> pd.Series:
    """Return a {0,1} long/flat position series: SMA trend AND
    below-threshold rolling excess-kurtosis regime."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    uptrend = close > sma

    log_ret = np.log(close / close.shift(1))
    excess_kurt = log_ret.rolling(kurtosis_window).kurt()

    pct_rank = excess_kurt.rolling(lookback, min_periods=kurtosis_window).apply(
        lambda x: (x < x[-1]).sum() / len(x), raw=True
    )

    calm_regime = pct_rank < kurtosis_pct_threshold
    position = (uptrend & calm_regime.fillna(False)).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret

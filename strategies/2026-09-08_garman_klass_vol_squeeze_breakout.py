"""Strategy: Garman-Klass volatility-percentile compression breakout.

Hypothesis (knowledge_base id=2026-09-08-023):
Per LuxAlgo's Garman-Klass Estimator library page
(https://www.luxalgo.com/library/indicator/garman-klass-estimator/), the
Garman-Klass (GK) estimator measures volatility from the WHOLE bar (high,
low, open, close) rather than closes alone: per-bar variance contribution
is 0.5*ln(H/L)^2 - (2*ln(2)-1)*ln(C/O)^2, averaged over a rolling window and
annualized. The source's own trading guidance: "Compression: the percentile
rank crossing under the low threshold flags a quiet stretch...that often
resolves into wider movement" and "Expansion: the rank crossing the high
threshold confirms volatility is broadening." This strategy operationalizes
that: when GK-vol's rolling percentile rank is compressed (below a low
threshold) and price then breaks above its own recent N-day high while
above a longer-term trend filter, that's a volatility-compression breakout
entry -- the compression should resolve into an expansion move that
continues in the breakout direction (uptrend already established).

First Garman-Klass-based strategy in this repo. Distinct from prior
Bollinger-Bandwidth-percentile squeeze strategies (2026-09-05-020 BBWP raw
lookback quantile, 2026-09-07-003 BBWP standard percentile rank) because GK
volatility uses the full OHLC range/gap information (open-close jump and
high-low range separately weighted), not derived from a Bollinger Band's
close-based standard deviation at all -- a mechanically different
volatility estimator, not just a different threshold on the same one.

Signal logic
------------
- Per-bar GK variance: 0.5*ln(H/L)^2 - (2*ln(2)-1)*ln(C/O)^2
- GK vol = sqrt(rolling_mean(gk_var, gk_window) * 252) (annualized)
- Percentile rank of current GK vol within its trailing `pct_lookback` bars
  (causal, no look-ahead: computed using only bars up to and including the
  current bar's window).
- Squeeze state: percentile rank <= squeeze_pct on the PRIOR bar (avoid
  same-bar look-ahead into the entry signal).
- Donchian breakout: close > rolling max(high, breakout_window) shifted by
  1 (prior N-day high, excluding today).
- Trend filter: close > SMA(trend_window).
- Entry (long): squeeze state on the prior bar AND today's close breaks
  above the prior breakout_window-day high AND close > SMA(trend_window).
- Exit: GK-vol percentile rank crosses above expand_pct (compression has
  fully resolved into expansion -- take profit on the vol move), OR close
  falls back below SMA(trend_window) (trend filter breaks), OR held >=
  max_hold_days time-stop.

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


def _garman_klass_vol(df: pd.DataFrame, gk_window: int) -> pd.Series:
    high, low, open_, close = df["high"], df["low"], df["open"], df["close"]
    log_hl = np.log(high / low)
    log_co = np.log(close / open_)
    gk_var_per_bar = 0.5 * (log_hl ** 2) - (2 * np.log(2) - 1) * (log_co ** 2)
    gk_var_mean = gk_var_per_bar.rolling(gk_window).mean().clip(lower=0)
    return np.sqrt(gk_var_mean * 252)


def _percentile_rank(series: pd.Series, lookback: int) -> pd.Series:
    def _rank(window: np.ndarray) -> float:
        last = window[-1]
        return float((window <= last).sum()) / len(window) * 100.0

    return series.rolling(lookback).apply(_rank, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    gk_window: int = 20,
    pct_lookback: int = 100,
    squeeze_pct: float = 20.0,
    expand_pct: float = 80.0,
    breakout_window: int = 20,
    trend_window: int = 100,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    gk_vol = _garman_klass_vol(df, gk_window)
    pct_rank = _percentile_rank(gk_vol, pct_lookback)

    squeeze_prior = (pct_rank.shift(1) <= squeeze_pct)
    prior_high = high.shift(1).rolling(breakout_window).max()
    breakout = close > prior_high

    trend_sma = close.rolling(trend_window, min_periods=trend_window // 2).mean()
    uptrend = close > trend_sma

    entry = squeeze_prior.fillna(False) & breakout.fillna(False) & uptrend.fillna(False)
    exit_expand = pct_rank > expand_pct
    exit_trend_break = ~uptrend.fillna(False)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_expand.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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

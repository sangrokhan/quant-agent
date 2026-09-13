"""Strategy: Double-percentile-rank volatility-regime switch between
RSI(2) mean-reversion and SMA(50/200) trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl, this id):
Per "Trading using Garch Volatility Forecast" (R-bloggers, 2012, citing
Quantum Financier's "Regime Switching System Using Volatility Forecast"):
https://www.r-bloggers.com/2012/01/trading-using-garch-volatility-forecast/
market regime can be classified via a SMOOTHED, DOUBLE percentile-rank of
realized volatility:

    ret_log      = log(close).diff()
    hist_vol     = rolling_std(ret_log, 21)
    vol_rank     = percent_rank( SMA( percent_rank(hist_vol, 252), 21 ), 250 )

When vol_rank > 0.5 (volatility itself is running high relative to its own
smoothed recent-percentile history -> "choppy/high-vol regime"), the source
claims a mean-reversion strategy (RSI(2): long when RSI(2) < 50) works
better; when vol_rank <= 0.5 ("calmer/trending regime"), a trend-following
SMA(50) vs SMA(200) crossover works better. Regime-switching between the two
should outperform running either alone across the full sample.

This repo enforces long-only (SAFETY.md), so the source's short legs are
dropped: in the mean-reversion regime we go long when RSI(2) < 50 else flat;
in the trend regime we go long when SMA(50) > SMA(200) else flat.

Distinct from this repo's prior rejected 3-filter ADX+ATR-pct+Hurst regime
switch (fortraders.com, ADX>25/Hurst>0.55 momentum vs ADX<20/Hurst<0.45
mean-reversion) -- that used discrete trend-strength/persistence indicators
as the regime gate. This strategy uses ONLY a smoothed double
percentile-rank of realized volatility itself as the regime gate, with no
ADX/Hurst/R-S involved -- a genuinely different regime-detection mechanism
applied to the same "switch between MR and TF" idea.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def _rolling_percent_rank(s: pd.Series, window: int) -> pd.Series:
    """Percentile rank (0-1) of the last value in each trailing window."""

    def _pr(x: np.ndarray) -> float:
        last = x[-1]
        return float((x <= last).sum()) / float(len(x))

    return s.rolling(window, min_periods=window).apply(_pr, raw=True)


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    hist_vol_window: int = 21,
    vol_rank_lookback: int = 252,
    vol_rank_smooth: int = 21,
    vol_rank_lookback2: int = 250,
    vol_rank_threshold: float = 0.5,
    rsi_period: int = 2,
    rsi_threshold: float = 50.0,
    sma_short: int = 50,
    sma_long: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ret_log = np.log(close / close.shift(1))
    hist_vol = ret_log.rolling(hist_vol_window, min_periods=hist_vol_window).std()

    pr1 = _rolling_percent_rank(hist_vol, vol_rank_lookback)
    pr1_smooth = pr1.rolling(vol_rank_smooth, min_periods=vol_rank_smooth).mean()
    vol_rank = _rolling_percent_rank(pr1_smooth, vol_rank_lookback2)

    high_vol_regime = vol_rank > vol_rank_threshold

    rsi2 = _rsi(close, rsi_period)
    mr_long = rsi2 < rsi_threshold

    sma_s = close.rolling(sma_short, min_periods=sma_short).mean()
    sma_l = close.rolling(sma_long, min_periods=sma_long).mean()
    tf_long = sma_s > sma_l

    position = pd.Series(0, index=close.index, dtype=int)
    long_signal = np.where(high_vol_regime.fillna(False), mr_long, tf_long)
    valid = (~vol_rank.isna()) & (~sma_l.isna())
    position[:] = np.where(valid, long_signal.astype(int), 0)
    return pd.Series(position, index=close.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

"""Strategy: GLD/UUP rolling-correlation regime gate + RSI(14) 30/70 crossover
mean-reversion signal on GLD (dollar-index proxy via UUP).

Hypothesis (knowledge_base id 2026-09-27-1xx, this cron trigger):
Per TradingView's "Gold/DXY Correlation Oscillator" (laraibislam, visited
this iteration, https://www.tradingview.com/script/e35VP2Mq-Gold-DXY-Correlation-Oscillator/):
gold and the US dollar typically move inversely. The indicator computes a
rolling Pearson correlation (default 20-30 bars) between gold's close and
DXY's close, and only enables RSI-based buy/sell signals when that
correlation is BELOW a threshold (default -0.3), i.e. when the normal
inverse relationship is actively in force -- suppressing signals during
regimes where the macro relationship has broken down (a documented source
of false entries per the source's own stated rationale). Signal generation
itself is a simple RSI(14) 30/70 crossover: buy when correlation is below
threshold AND RSI crosses above 30 (oversold recovery); sell/exit when
correlation is below threshold AND RSI crosses below 70 (overbought
reversal), i.e. exits when the recovering-from-oversold-entry no longer
holds under the active regime.

This repo lacks true DXY futures data via data/loaders.py (yfinance/ccxt
OHLCV only) -- as established in prior entries (2026-09-11-058), UUP
(Invesco DB US Dollar Index Bullish Fund ETF) is used as the standard DXY
proxy. This is the first strategy in this repo to combine a rolling
Pearson CORRELATION regime gate (not a simple ratio/level/z-score construct
like every prior GLD/DXY or GLD/UUP entry) with an RSI mean-reversion
crossover trigger -- distinct from all prior DXY-regime-filter entries
(SMA-level gate 2026-09-05-026, ROC-momentum gate 2026-09-09-113, two-level
absolute-threshold hysteresis 2026-09-20-026, rolling-correlation-breakdown
gate on BTC 2026-09-23-021 -- none combine a correlation regime filter with
an RSI oversold/overbought crossover trigger, and none are on GLD as the
primary asset). Applied on GLD (equity/commodity-ETF ticker via
load_equity) and, as a cross-asset generalization test, BTC/USDT and
ETH/USDT (crypto) using each asset's own rolling correlation with UUP.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} long/flat)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def _dxy_proxy_close(index: pd.DatetimeIndex) -> pd.Series:
    from loaders import load_equity

    start = index.min() - pd.Timedelta(days=60)
    end = index.max() + pd.Timedelta(days=5)
    uup = _prep(load_equity("UUP", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]
    uup = uup.reindex(index, method="ffill")
    return uup


def generate_signals(
    price_df: pd.DataFrame,
    corr_window: int = 90,
    corr_threshold: float = -0.6,
    rsi_period: int = 10,
    rsi_oversold: float = 35.0,
    rsi_overbought: float = 65.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    dxy_proxy = _dxy_proxy_close(close.index)
    rolling_corr = close.rolling(corr_window).corr(dxy_proxy)

    rsi = _rsi(close, rsi_period)

    regime_active = rolling_corr < corr_threshold

    buy_signal = (rsi > rsi_oversold) & (rsi.shift(1) <= rsi_oversold) & regime_active
    sell_signal = (rsi < rsi_overbought) & (rsi.shift(1) >= rsi_overbought) & regime_active

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    warmup = max(corr_window, rsi_period) + 5

    buy_arr = buy_signal.to_numpy()
    sell_arr = sell_signal.to_numpy()

    for i in range(len(close)):
        if i < warmup or not np.isfinite(rolling_corr.iloc[i]) or not np.isfinite(rsi.iloc[i]):
            position.iloc[i] = 0
            continue
        if in_pos:
            if bool(sell_arr[i]):
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(buy_arr[i]):
                in_pos = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    corr_window: int = 90,
    corr_threshold: float = -0.6,
    rsi_period: int = 10,
    rsi_oversold: float = 35.0,
    rsi_overbought: float = 65.0,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    positions = generate_signals(
        price_df,
        corr_window=corr_window,
        corr_threshold=corr_threshold,
        rsi_period=rsi_period,
        rsi_oversold=rsi_oversold,
        rsi_overbought=rsi_overbought,
    )
    daily_returns = close.pct_change().fillna(0.0)
    strategy_returns = positions.shift(1).fillna(0).astype(float) * daily_returns
    return strategy_returns

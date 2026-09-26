"""Strategy: RSI(2) mean reversion gated by a HIGH volatility (NATR) regime.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-013):
Per Quantitativo's "Trading the mean reversion curve"
(https://www.quantitativo.com/p/trading-the-mean-reversion-curve, free
disclosed finding): re-examining the classic RSI(2)<5 + close>SMA(200)
Nasdaq-100 mean-reversion edge, the article's own disclosed chart
("Impact of the NATR on the Expected Return") shows the edge's expected
return increases monotonically with the stock's own Normalized ATR
(NATR = ATR/close) at entry -- i.e. "the higher the volatility, the higher
the expected return in these short-term mean-reversion trades." This is
the OPPOSITE gate direction from this repo's existing accepted RSI(2)+ATR%
strategies (2026-09-20-140/2026-09-23-045, both gate to LOW-vol regimes
per a different source's finding that low-vol improves RSI(2) profit
factor). This strategy tests the Quantitativo HIGH-vol gate directly:
long when RSI(2) < entry_threshold AND close > SMA(200) AND NATR(14) is
ABOVE its own trailing rolling median (high-vol regime), exit when RSI(2)
crosses back above exit_threshold or a max_hold_days time-stop.

First strategy in this repo to gate RSI(2) mean-reversion to a HIGH-vol
(rather than low-vol) regime -- directly testing whether Quantitativo's
own disclosed NATR-return relationship (measured on Nasdaq-100
constituents cross-sectionally) transfers to single-symbol index-ETF
mean-reversion in this repo's architecture.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 2,
    entry_threshold: float = 5.0,
    exit_threshold: float = 60.0,
    trend_ma_window: int = 200,
    atr_window: int = 14,
    natr_median_lookback: int = 100,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    rsi = _rsi(close, rsi_window)
    trend_ok = close > close.rolling(trend_ma_window).mean()

    atr = _atr(high, low, close, atr_window)
    natr = (atr / close) * 100.0
    natr_median = natr.rolling(natr_median_lookback).median()
    high_vol_regime = natr > natr_median

    entry = (rsi < entry_threshold) & trend_ok & high_vol_regime.fillna(False)
    exit_signal = rsi > exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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

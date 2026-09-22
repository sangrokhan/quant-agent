"""Strategy: Dual Hull Moving Average (HMA) crossover, gated by an RSI
momentum-confirmation filter and a linear-regression trend-regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-028):
Source: Google AI Overview synthesis (search query "Hull Moving Average
crossover trading strategy specific period rule backtest", citing a
YouTube channel "CodeTrading" HMA crossover system), read via browser_exec
Google SERP fallback (web_search DDGS backend errored on this iteration's
query). The disclosed rule set:
  - Fast HMA(16) crossing above Slow HMA(65) is the base long signal.
  - Momentum confirmation: RSI(14) must be > 52 at the time of the cross.
  - Regime filter: price must be in an uptrend per a 50-period linear
    regression slope being positive (avoids trading the crossover against
    the prevailing trend).
  - Exit: Fast HMA(16) crosses back below Slow HMA(65).
The source's native setup is a 4H execution timeframe with a daily regime
filter (crypto-oriented). This repo's data/loaders.py exposes 1d bars for
equities and (by default) 1h bars for crypto, not 4H, so this
implementation adapts the *rule logic* (dual HMA crossover + RSI
confirmation + linear-regression trend regime) to whatever bar frequency
the loader returns, rather than trying to replicate the exact multi-timeframe
setup. This is distinct from the previously-tested single-HMA price-cross
strategy (2026-09-04-026, rejected near-miss) -- here we use a DUAL HMA
crossover (not price vs single HMA) plus two additional confirmation
filters (RSI momentum + linear-regression regime), which is a materially
different rule, not a parameter retune of the earlier idea.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = np.arange(1, window + 1)
    return series.rolling(window).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def _hma(series: pd.Series, window: int) -> pd.Series:
    """Hull Moving Average: WMA(2*WMA(n/2) - WMA(n), sqrt(n))."""
    half = max(int(window / 2), 1)
    sqrt_n = max(int(round(window ** 0.5)), 1)
    wma_half = _wma(series, half)
    wma_full = _wma(series, window)
    raw_hma = 2 * wma_half - wma_full
    return _wma(raw_hma, sqrt_n)


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _rolling_linreg_slope(series: pd.Series, window: int) -> pd.Series:
    """Rolling linear-regression slope of `series` over `window` bars."""
    x = np.arange(window)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    def _slope(y: np.ndarray) -> float:
        y_mean = y.mean()
        return float(((x - x_mean) * (y - y_mean)).sum() / x_var)

    return series.rolling(window).apply(_slope, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    fast_period: int = 16,
    slow_period: int = 65,
    rsi_period: int = 14,
    rsi_threshold: float = 52.0,
    trend_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_hma = _hma(close, fast_period)
    slow_hma = _hma(close, slow_period)
    rsi = _rsi(close, rsi_period)
    slope = _rolling_linreg_slope(close, trend_window)

    bullish_cross = (fast_hma > slow_hma) & (fast_hma.shift(1) <= slow_hma.shift(1))
    bearish_cross = (fast_hma < slow_hma) & (fast_hma.shift(1) >= slow_hma.shift(1))

    entry = bullish_cross & (rsi > rsi_threshold) & (slope > 0)
    exit_ = bearish_cross

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    pos_vals = []
    for i in range(len(close)):
        if not in_pos and bool(entry.iloc[i]):
            in_pos = True
        elif in_pos and bool(exit_.iloc[i]):
            in_pos = False
        pos_vals.append(1 if in_pos else 0)
    position = pd.Series(pos_vals, index=close.index, dtype=int)
    position = position.fillna(0).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    fast_period: int = 16,
    slow_period: int = 65,
    rsi_period: int = 14,
    rsi_threshold: float = 52.0,
    trend_window: int = 50,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        fast_period=fast_period,
        slow_period=slow_period,
        rsi_period=rsi_period,
        rsi_threshold=rsi_threshold,
        trend_window=trend_window,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = (position.shift(1).fillna(0) * daily_ret).fillna(0.0)
    return strat_ret

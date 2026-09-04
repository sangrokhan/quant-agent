"""Strategy: Traders Dynamic Index (TDI, Dean Malone) long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-117):
The Traders Dynamic Index (TDI) is an all-in-one RSI + Bollinger Band
indicator: a 13-day RSI, its fast (2-day SMA) and slow (7-day SMA)
moving averages, and 34-day Bollinger Bands (1.6185 std) of the RSI
itself (upper/middle/lower bands). Source (quantifiedstrategies.com)
gives explicit free trading rules and backtests it on SPY: worse absolute
CAGR than buy-and-hold but much better risk-adjusted return (far smaller
max drawdown, only ~29% time in market). We test the same rule set here
via the standard grid/validator pipeline.

Rules (source's exact wording)
-------------------------------
BUY when:
  fast RSI-MA > middle band AND slow RSI-MA > middle band AND
  fast RSI-MA < upper band
SELL (exit) when:
  (fast RSI-MA > 70 AND slow RSI-MA > 70) OR
  (fast RSI-MA < middle band AND slow RSI-MA < middle band)

A max_hold_days safety time-stop is added (source gives no explicit stop).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept params as keyword args.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0, 100.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 13,
    fast_ma: int = 2,
    slow_ma: int = 7,
    bb_window: int = 34,
    bb_std: float = 1.6185,
    overbought: float = 70.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"].astype(float)

    rsi = _rsi(close, rsi_period)
    fast_rsi_ma = rsi.rolling(fast_ma, min_periods=fast_ma).mean()
    slow_rsi_ma = rsi.rolling(slow_ma, min_periods=slow_ma).mean()

    mid_band = rsi.rolling(bb_window, min_periods=bb_window).mean()
    std = rsi.rolling(bb_window, min_periods=bb_window).std()
    upper_band = mid_band + bb_std * std
    # lower_band not needed for this rule set, but kept for completeness

    entry = (
        (fast_rsi_ma > mid_band)
        & (slow_rsi_ma > mid_band)
        & (fast_rsi_ma < upper_band)
    ).fillna(False)

    exit_signal = (
        ((fast_rsi_ma > overbought) & (slow_rsi_ma > overbought))
        | ((fast_rsi_ma < mid_band) & (slow_rsi_ma < mid_band))
    ).fillna(False)

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
    close = df["close"].astype(float)
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

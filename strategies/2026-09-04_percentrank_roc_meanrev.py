"""Strategy: PercentRank(ROC) mean reversion (Cesar Alvarez), trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-121):
Instead of a raw Rate-of-Change (ROC) threshold to detect a sell-off
(which doesn't normalize across low/high volatility names), Cesar Alvarez
(alvarezquanttrading.com) proposes ranking today's short-term ROC against
its own trailing-year history via PercentRank: PercentRank(252) of
ROC(roc_period) below a low threshold (~5-15) flags an extreme,
volatility-normalized sell-off regardless of the stock's baseline
volatility. Source's full rule set: setup = close > SMA(100) (long-term
uptrend) AND 252-day PercentRank of ROC(2) < entry_pct_rank; exit when
RSI(2) > exit_rsi_threshold. We simplify the entry to a same-day market
entry (source uses a limit order 1/2*ATR below the previous close, which
we don't simulate here) and add a max_hold_days safety time-stop.

Formula
-------
ROC(roc_period)[i] = 100 * (close[i] / close[i-roc_period] - 1)
PercentRank(lookback)[i] = 100 * (count of j in the trailing `lookback`
    window where ROC[j] <= ROC[i]) / lookback

Signal logic
------------
- Entry (long): close > SMA(trend_window) AND PercentRank(lookback) of
  ROC(roc_period) < entry_pct_rank.
- Exit: RSI(2) > exit_rsi_threshold, OR a max_hold_days time-stop.
- Flat otherwise.

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


def _percent_rank(series: pd.Series, lookback: int) -> pd.Series:
    def _rank(window):
        current = window[-1]
        return 100.0 * (window <= current).sum() / len(window)

    return series.rolling(lookback, min_periods=lookback).apply(_rank, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    roc_period: int = 2,
    lookback: int = 252,
    entry_pct_rank: float = 5.0,
    trend_window: int = 100,
    exit_rsi_threshold: float = 40.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"].astype(float)

    roc = 100.0 * (close / close.shift(roc_period) - 1.0)
    pct_rank = _percent_rank(roc, lookback)
    sma_trend = close.rolling(trend_window, min_periods=trend_window).mean()
    rsi2 = _rsi(close, 2)

    entry = ((close > sma_trend) & (pct_rank < entry_pct_rank)).fillna(False)
    exit_signal = (rsi2 > exit_rsi_threshold).fillna(False)

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

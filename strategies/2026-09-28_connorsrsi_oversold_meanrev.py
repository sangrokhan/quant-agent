"""Strategy: ConnorsRSI (CRSI) composite mean-reversion, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-28-044),
sourced from https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/connorsrsi
(StockCharts ChartSchool, read via browser_exec -- web_extract ddgs backend
is search-only and cannot extract URL content) and corroborated via
backtrader.com/wealthcharts.com/quantifiedstrategies.com's identical
formula statement seen in the search snippets this iteration.

ConnorsRSI (Larry Connors / Connors Research) is a composite of THREE
separate 0-100-bounded components, averaged:
  1. RSI(rsi_period) -- standard Wilder RSI of price, default period=3.
  2. StreakRSI = RSI(streak_period) of the up/down STREAK LENGTH (number
     of consecutive days closed up in a row, or negative for consecutive
     days closed down; resets to 0 on an unchanged close), default
     streak_period=2.
  3. PercentRank(roc_lookback) of the 1-bar rate of change: the percentile
     rank of today's 1-day pct-change among the trailing roc_lookback
     values (default 100).

CRSI = (RSI(rsi_period) + StreakRSI(streak_period) + PercentRank(roc_lookback)) / 3

Source's own recommended interpretation: CRSI < oversold_threshold
(default 10, or 5 for more volatile securities) is a buying opportunity;
CRSI > overbought_threshold (default 90) signals a pullback. This repo
has tested Larry Connors' simpler RSI(2) strategy and the "Double Seven"
strategy before, but never the actual 3-component ConnorsRSI composite
indicator itself (0 prior "ConnorsRSI"/"CRSI" hits for the composite
formula in strategies_index.jsonl) -- distinct mechanism since it also
incorporates trend-duration (streak) and magnitude-of-move (percent rank)
components beyond plain price RSI.

Signal logic (daily bars, causal/no look-ahead):
1. Trend filter: close > SMA(trend_window) (default 200d) -- per Connors'
   own broader "Short Term Trading Strategies That Work" methodology of
   only buying oversold dips within an established uptrend (same
   convention already used for this repo's RSI(2) strategy).
2. Entry (long): CRSI crosses below oversold_threshold (default 10) AND
   the uptrend filter holds.
3. Exit: CRSI crosses back above exit_threshold (default 50, Connors'
   own "return to the mean" exit convention for RSI(2)-family strategies,
   reused here since ConnorsRSI's own site doesn't specify an explicit
   exit rule beyond the overbought level) OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
validation/grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def _wilder_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0, 100.0)
    rsi = rsi.where(avg_gain != 0, 0.0)
    return rsi


def _streak(close: pd.Series) -> pd.Series:
    """Up/down streak length: +N for N consecutive up-closes in a row,
    -N for N consecutive down-closes, 0 reset on an unchanged close."""
    diff_sign = np.sign(close.diff())
    streak = pd.Series(0.0, index=close.index)
    current = 0.0
    values = diff_sign.values
    out = np.zeros(len(close))
    for i in range(len(close)):
        s = values[i]
        if np.isnan(s) or s == 0:
            current = 0.0
        elif s > 0:
            current = current + 1 if current >= 0 else 1.0
        else:
            current = current - 1 if current <= 0 else -1.0
        out[i] = current
    return pd.Series(out, index=close.index)


def _percent_rank(series: pd.Series, lookback: int) -> pd.Series:
    def _rank_last(window):
        if len(window) < 2:
            return np.nan
        last = window.iloc[-1]
        return 100.0 * (window[:-1] < last).sum() / (len(window) - 1)

    return series.rolling(lookback + 1, min_periods=lookback + 1).apply(_rank_last, raw=False)


def _connors_rsi(
    close: pd.Series,
    rsi_period: int,
    streak_period: int,
    roc_lookback: int,
) -> pd.Series:
    rsi_component = _wilder_rsi(close, rsi_period)
    streak = _streak(close)
    streak_rsi_component = _wilder_rsi(streak, streak_period)
    one_bar_roc = close.pct_change()
    percent_rank_component = _percent_rank(one_bar_roc, roc_lookback)
    return (rsi_component + streak_rsi_component + percent_rank_component) / 3.0


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 3,
    streak_period: int = 2,
    roc_lookback: int = 100,
    trend_window: int = 200,
    oversold_threshold: float = 10.0,
    exit_threshold: float = 50.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    crsi = _connors_rsi(close, rsi_period, streak_period, roc_lookback)

    entry = (crsi < oversold_threshold) & uptrend.fillna(False)
    exit_signal = crsi > exit_threshold

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

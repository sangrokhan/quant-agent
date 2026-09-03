"""Strategy: Larry Connors RSI(2) mean-reversion, trend-filtered by 200d SMA.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-005), sourced
from https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2
(StockCharts ChartSchool's writeup of Larry Connors' 2-period RSI strategy):

    1. Long-term trend filter: close > 200-day SMA (only take long trades in
       an established uptrend -- Connors' rule; we go long-only, no shorting,
       per this repo's SAFETY.md convention and prior strategies).
    2. Entry trigger: RSI(2) (2-period Wilder RSI on closing prices) closes
       below an oversold threshold (Connors found 5 stronger than 10 -- we
       use 5 as default, exposed as a tunable param `rsi_entry`).
    3. Exit: close back above the 5-day SMA (`exit_sma_window`, default 5) --
       a fast mean-reversion exit, not a trend-following hold.

This differs materially from every strategy already tried in this repo's
knowledge base: prior strategies were either MA-crossover trend-following
(2026-09-01-001), Bollinger-band mean-reversion (2026-09-03-001), or
absolute/trend-filtered momentum (2026-09-03-002/-003/-004). This is the
first RSI-oscillator-based, fast-holding-period (few days) mean-reversion
entry combined with a long-term trend gate -- conceptually the *opposite*
holding-period profile of the momentum family (short, sharp mean-reversion
dips within an uptrend, vs. multi-week/month trend-following).

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    """Wilder's RSI (standard exponential smoothing, alpha=1/window)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    # When avg_loss is 0 (all gains), RSI -> 100.
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 2,
    rsi_entry: float = 5.0,
    trend_window: int = 200,
    exit_sma_window: int = 5,
) -> pd.Series:
    """Long-only {0,1} position series.

    Entry: close > trend SMA(trend_window) AND RSI(rsi_window) <= rsi_entry
    (deeply oversold dip within an established uptrend).
    Exit: close > SMA(exit_sma_window) (fast mean-reversion exit) OR the
    trend filter breaks (close <= trend SMA), whichever comes first.
    Position is held (stateful) between entry and exit, not re-evaluated
    fresh every bar -- this matches Connors' actual rule (hold until the
    5-day-SMA exit fires), not just "RSI < 5 today".
    """
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_window)
    trend_sma = close.rolling(trend_window).mean()
    exit_sma = close.rolling(exit_sma_window).mean()

    above_trend = (close > trend_sma).fillna(False)
    entry_trigger = (above_trend & (rsi <= rsi_entry)).fillna(False)
    exit_trigger = ((close > exit_sma) | (~above_trend)).fillna(True)

    in_position = False
    pos_vals = [0] * len(close)
    entry_vals = entry_trigger.values
    exit_vals = exit_trigger.values
    for i in range(len(pos_vals)):
        if in_position:
            if exit_vals[i]:
                in_position = False
                pos_vals[i] = 0
            else:
                pos_vals[i] = 1
        else:
            if entry_vals[i]:
                in_position = True
                pos_vals[i] = 1
            else:
                pos_vals[i] = 0
    position = pd.Series(pos_vals, index=close.index, dtype=int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift position by 1 day: yesterday's signal determines today's exposure
    # (avoid look-ahead bias -- can't trade on today's own close).
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

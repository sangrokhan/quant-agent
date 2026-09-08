"""Strategy: Larry Connors' Cumulative RSI(2), 200-day SMA trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-002):
Per Larry Connors' "Short Term Trading Strategies That Work" (as disclosed
and independently reproduced/discussed at
https://www.elitetrader.com/et/threads/larry-connors-cumulative-rsi-26-annual-return-now-with-sensitivity-analysis.379982/):
summing (not averaging/compositing) RSI(2) over the last `cum_window` days
into a single "cumulative RSI" gives a statistical edge over the vanilla
single-day RSI(2) oversold/overbought signal, because it requires SEVERAL
consecutive days of weak momentum rather than a single snapshot reading.
Rules per source: buy next open when 2-day cumulative RSI(2) < 10; exit
next open when cumulative RSI(2) > 65; only trade when price is above its
200-day SMA (source also exits immediately if price closes below the
200-day SMA while holding). This is a genuinely new indicator construction
in this repo -- SUM of a short RSI window across days, distinct from
Connors RSI (2026-09-04-113, a 3-way composite average of RSI(3) + streak
RSI(2) + PercentRank(ROC)) and from plain RSI(2) mean reversion
(2026-09-03-005, single-day snapshot, no cumulative/summed construction).

Signal logic
------------
- RSI2 = RSI(close, window=2) via Wilder smoothing.
- Cumulative RSI = rolling sum of RSI2 over the trailing `cum_window` days
  (source's own default cum_window=2).
- Trend filter: close > SMA(trend_window) (source's own 200-day SMA gate).
- Entry (long): cumulative RSI crosses below entry_threshold AND
  close > SMA(trend_window).
- Exit: cumulative RSI crosses above exit_threshold, OR close falls below
  SMA(trend_window) (source's own immediate trend-break exit), OR a
  max_hold_days safety time-stop (source doesn't specify one explicitly for
  the single-symbol version; added here purely as a risk backstop,
  consistent with this repo's convention).
- Position lagged by one bar to approximate "enter/exit at next open"
  execution timing on daily OHLC bars.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 2,
    cum_window: int = 2,
    entry_threshold: float = 10.0,
    exit_threshold: float = 65.0,
    trend_window: int = 200,
    max_hold_days: int = 15,
    execution_lag: int = 1,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi2 = _rsi(close, rsi_window)
    cum_rsi = rsi2.rolling(cum_window).sum()
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    cross_below_entry = (cum_rsi < entry_threshold) & (cum_rsi.shift(1) >= entry_threshold)
    cross_above_exit = (cum_rsi > exit_threshold) & (cum_rsi.shift(1) <= exit_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_count = 0
    for i in range(len(close)):
        if in_position:
            hold_count += 1
            if cross_above_exit.iloc[i] or (not uptrend.iloc[i]) or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
            else:
                position.iloc[i] = 1
        else:
            if cross_below_entry.iloc[i] and uptrend.iloc[i]:
                in_position = True
                hold_count = 0
                position.iloc[i] = 1

    if execution_lag:
        position = position.shift(execution_lag).fillna(0).astype(int)

    return position


def generate_returns(
    price_df: pd.DataFrame,
    rsi_window: int = 2,
    cum_window: int = 2,
    entry_threshold: float = 10.0,
    exit_threshold: float = 65.0,
    trend_window: int = 200,
    max_hold_days: int = 15,
    execution_lag: int = 1,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        rsi_window=rsi_window,
        cum_window=cum_window,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
        execution_lag=execution_lag,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_returns
    return strat_returns

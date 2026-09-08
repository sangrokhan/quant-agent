"""Strategy: QS RSI unconditional mean-reversion, next-bar execution (no trend gate).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-001):
QuantifiedStrategies.com's "QS RSI: A Simple Indicator for Short-Term Mean
Reversion" article (https://www.quantifiedstrategies.com/qs-rsi-a-simple-indicator-for-short-term-mean-reversion/,
fully discloses the formula and gives one concrete example strategy) states:
"Entry: QS RSI below 10 -> Buy next open. Exit: QS RSI above 65 -> Sell next
open." This is UNCONDITIONAL (no 200-day SMA trend filter) and uses tighter
published thresholds (10/65) than this repo's already-accepted QQQ/SPY QS
RSI variant (2026-09-04-164, entry=20/exit=70, WITH a 200-day SMA uptrend
gate). Distinct novelty angle from -164: (a) no trend filter at all -- tests
whether QS RSI's oversold signal alone (no regime gate) is sufficient,
matching the source's own stated simplest form; (b) tighter/more extreme
thresholds (10 vs 20 entry, 65 vs 70 exit) per the source's own worked
example, not a re-run of the already-tested wider thresholds.

Signal logic
------------
- RSI3 = RSI(close, window=3) via Wilder smoothing.
- Day-range position = (close - low) / (high - low) * 100 (IBS scaled to
  0-100, single-day).
- N-day-range position = (close - rolling_Nd_low) / (rolling_Nd_high -
  rolling_Nd_low) * 100.
- QS_RSI = mean(RSI3, day_range_position, N_day_range_position).
- Entry (long): QS_RSI crosses below entry_threshold (no trend filter).
- Exit: QS_RSI crosses above exit_threshold, OR a max_hold_days safety
  time-stop (source doesn't specify one; added here purely as a risk
  backstop against unbounded holds, consistent with this repo's convention).
- Position is lagged by one additional bar vs. the raw signal (approximates
  the source's own "next open" execution timing on daily OHLC bars where we
  only have close-based signals).
- Flat otherwise.

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


def _qs_rsi(df: pd.DataFrame, rsi_window: int, range_window: int) -> pd.Series:
    close, high, low = df["close"], df["high"], df["low"]

    rsi_n = _rsi(close, rsi_window)

    day_range = (high - low).replace(0.0, np.nan)
    day_pos = ((close - low) / day_range * 100.0).fillna(50.0)

    roll_low = low.rolling(range_window).min()
    roll_high = high.rolling(range_window).max()
    roll_range = (roll_high - roll_low).replace(0.0, np.nan)
    rangeN_pos = ((close - roll_low) / roll_range * 100.0).fillna(50.0)

    qs_rsi = (rsi_n + day_pos + rangeN_pos) / 3.0
    return qs_rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 3,
    range_window: int = 5,
    entry_threshold: float = 10.0,
    exit_threshold: float = 65.0,
    max_hold_days: int = 15,
    execution_lag: int = 1,
) -> pd.Series:
    """Return a {0,1} long/flat position series, unconditional (no trend gate)."""
    df = _prep(price_df)
    close = df["close"]

    qs_rsi = _qs_rsi(df, rsi_window, range_window)

    cross_below_entry = (qs_rsi < entry_threshold) & (qs_rsi.shift(1) >= entry_threshold)
    cross_above_exit = (qs_rsi > exit_threshold) & (qs_rsi.shift(1) <= exit_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_count = 0
    for i in range(len(close)):
        if in_position:
            hold_count += 1
            if cross_above_exit.iloc[i] or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
            else:
                position.iloc[i] = 1
        else:
            if cross_below_entry.iloc[i]:
                in_position = True
                hold_count = 0
                position.iloc[i] = 1

    # Approximate "next open" execution timing: lag the position by one
    # extra bar (signal computed on close[t] is acted on at open[t+1]).
    if execution_lag:
        position = position.shift(execution_lag).fillna(0).astype(int)

    return position


def generate_returns(
    price_df: pd.DataFrame,
    rsi_window: int = 3,
    range_window: int = 5,
    entry_threshold: float = 10.0,
    exit_threshold: float = 65.0,
    max_hold_days: int = 15,
    execution_lag: int = 1,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        rsi_window=rsi_window,
        range_window=range_window,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        max_hold_days=max_hold_days,
        execution_lag=execution_lag,
    )

    daily_returns = close.pct_change().fillna(0.0)
    # Position held during day t earns day t's return (position already
    # incorporates the next-bar execution lag above).
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_returns
    return strat_returns

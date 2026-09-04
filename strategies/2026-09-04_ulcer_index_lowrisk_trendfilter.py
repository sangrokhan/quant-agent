"""Strategy: Ulcer Index low-risk regime entry with trend confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-144):
The Ulcer Index (Peter Martin, 1987) measures downside risk via the
root-mean-square of percentage retracements from the rolling N-day peak
(depth AND duration of drawdowns, not just volatility). Per Google's
AI-overview synthesis of StockCharts/Capital.com/PatternsWizard
explainers, a LOW Ulcer Index reading (shallow/brief drawdowns, below an
entry_threshold) combined with price above its own N-day SMA trend filter
signals a "calm uptrend" worth a long entry; exit when the Ulcer Index
rises above an elevated exit_threshold (drawdowns deepening, distress
building) or the trend filter breaks, plus a max_hold_days time-stop
backstop. First Ulcer-Index-based strategy tried in this repo (distinct
from ATR/realized-vol-based regime filters already tested -- Ulcer Index
specifically weights DOWNSIDE retracement depth, not two-sided volatility).

Signal logic
------------
- rolling_max = close.rolling(ui_window).max()
- pct_drawdown = 100 * (close - rolling_max) / rolling_max  (<=0)
- ulcer_index = sqrt(mean(pct_drawdown**2)) over ui_window (RMS of
  retracement depth).
- trend_ma = close.rolling(trend_window).mean()
- Entry (long): ulcer_index < entry_threshold AND close > trend_ma.
- Exit: ulcer_index > exit_threshold, OR close < trend_ma, OR a
  max_hold_days time-stop backstop.
- Flat otherwise (long-only; no short leg per SAFETY.md scope).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _ulcer_index(close: pd.Series, window: int) -> pd.Series:
    rolling_max = close.rolling(window, min_periods=max(2, window // 3)).max()
    pct_drawdown = 100.0 * (close - rolling_max) / rolling_max
    sq_dd = pct_drawdown ** 2
    ulcer = np.sqrt(sq_dd.rolling(window, min_periods=max(2, window // 3)).mean())
    return ulcer


def generate_signals(
    price_df: pd.DataFrame,
    ui_window: int = 14,
    entry_threshold: float = 3.0,
    exit_threshold: float = 6.0,
    trend_window: int = 50,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ulcer = _ulcer_index(close, ui_window)
    trend_ma = close.rolling(trend_window, min_periods=max(5, trend_window // 5)).mean()

    trend_ok = close > trend_ma
    low_risk = ulcer < entry_threshold
    high_risk = ulcer > exit_threshold

    entry = low_risk.fillna(False) & trend_ok.fillna(False)
    exit_signal = high_risk.fillna(False) | (~trend_ok.fillna(False))

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

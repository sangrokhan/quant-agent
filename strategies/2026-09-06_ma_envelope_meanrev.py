"""Strategy: Moving Average Envelope (percentage bands) mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-106),
sourced from:
  - Google AI-overview synthesis of Moving Average Envelope trading rules
    (TradingView/Definedge Securities/LightningChart/YouTube sources):
    "Central Line: 20-50 period SMA/EMA. Upper Band = MA*(1+pct). Lower Band
    = MA*(1-pct). Percentage Offset commonly 2-6%... Mean Reversion (Sideways
    / Ranging Markets): Long Entry: price touches or drops below the lower
    band, and a candle then closes back inside the envelope boundary. Exit
    Target: take profit near the central moving average line."
  - https://www.quantifiedstrategies.com/moving-average-envelope/ (confirms
    default 20-period SMA, +/-5% envelope is the common default; SPY
    backtest disclosed 194 trades/6.9% CAGR/73% win rate/-15% MDD/25% time
    invested; exact numeric entry/exit thresholds paywalled; article notes
    the optimization sweet spot tends toward a SHORTER lookback with a
    SMALLER envelope pct, and that best settings vary by asset).

First Moving-Average-Envelope-family strategy in this repo -- distinct from
Bollinger Bands (std-dev based bands) and Keltner Channels (ATR-based bands)
already tested here, since the envelope width here is a fixed PERCENTAGE of
the moving average rather than a volatility measure.

Signal logic
------------
- MA[t] = SMA(close, ma_window)[t].
- Lower band[t] = MA[t] * (1 - envelope_pct).
- Upper band[t] = MA[t] * (1 + envelope_pct).
- Long entry: close crosses back ABOVE the lower band after having closed at
  or below it the prior bar (the "touches/drops below then closes back
  inside" trigger from the source, operationalized as a 1-bar close-based
  cross to keep it mechanically testable without candle-pattern subjectivity).
- Exit: close reaches/crosses back above the central MA line (source's own
  stated take-profit target), or a max_hold_days time-stop (repo standard
  safety valve; source's own backtest reports a -15% MDD with an
  unspecified/no explicit stop-loss).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
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


def _envelope(df: pd.DataFrame, ma_window: int, envelope_pct: float) -> tuple[pd.Series, pd.Series, pd.Series]:
    ma = df["close"].rolling(ma_window, min_periods=ma_window).mean()
    lower = ma * (1.0 - envelope_pct)
    upper = ma * (1.0 + envelope_pct)
    return ma, lower, upper


def generate_signals(
    price_df: pd.DataFrame,
    ma_window: int = 20,
    envelope_pct: float = 0.05,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ma, lower, upper = _envelope(df, ma_window, envelope_pct)

    was_below_or_at = close.shift(1) <= lower.shift(1)
    crossed_back_up = (close > lower) & was_below_or_at.fillna(False)

    reached_ma = close >= ma

    entry_arr = crossed_back_up.fillna(False).values
    exit_arr = reached_ma.fillna(False).values

    n = len(df)
    position = np.zeros(n, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if not in_pos:
            if entry_arr[i]:
                in_pos = True
                hold_count = 0
        else:
            hold_count += 1
            if exit_arr[i] or hold_count >= max_hold_days:
                in_pos = False
        position[i] = 1 if in_pos else 0

    return pd.Series(position, index=df.index, name="position")


def generate_returns(
    price_df: pd.DataFrame,
    ma_window: int = 20,
    envelope_pct: float = 0.05,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df, ma_window=ma_window, envelope_pct=envelope_pct, max_hold_days=max_hold_days
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns

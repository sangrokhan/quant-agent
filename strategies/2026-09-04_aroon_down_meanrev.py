"""Strategy: Aroon-Down mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-031):
Per QuantifiedStrategies.com's Aroon indicator article
(https://www.quantifiedstrategies.com/aroon-indicator-strategy/,
"Strategy no 1", their own classical mean-reversion backtest): buy when
Aroon-Down < 10 (a very recent new low just occurred, i.e. a fresh
downtrend extreme), sell when Aroon-Down > 50 (downtrend momentum has
faded/reversed enough that the most recent low is no longer "recent").
Source's own SPY backtest (14-day Aroon period): 252 trades, avg gain
0.44%/trade, win rate 56%, MDD 23%, profit factor 1.5. Aroon-Down =
((period - days_since_period_low) / period) * 100 -- a pure ELAPSED-TIME
measure since the rolling low, distinct calculation basis from every
prior oscillator tested in this repo (RSI, CCI, stochastic, Williams %R
all use price-MAGNITUDE ratios; Aroon uses only time-since-extreme).

Signal logic
------------
- Aroon-Down(aroon_window) = ((aroon_window - days_since_period_low) /
  aroon_window) * 100, where days_since_period_low is the number of bars
  since the lowest low within the trailing aroon_window-bar window
  (0 = today is the new low).
- Entry (long): Aroon-Down < oversold_threshold (source: 10) -- a very
  fresh new low.
- Exit: Aroon-Down > exit_threshold (source: 50) -- the low is no longer
  recent, downtrend momentum has faded.
- Flat otherwise; long-only, no shorting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _aroon_down(low: pd.Series, aroon_window: int) -> pd.Series:
    # rolling window includes today; argmin returns the position (0-based,
    # 0 = oldest in the window) of the lowest low within the trailing
    # window. days_since_period_low = (window_len - 1) - argmin_position.
    def _days_since_low(x):
        # x is a numpy array, most recent value is x[-1]
        pos_of_min = x.argmin()  # 0-based from the start of the window
        return (len(x) - 1) - pos_of_min

    days_since = low.rolling(aroon_window).apply(_days_since_low, raw=True)
    aroon_down = ((aroon_window - days_since) / aroon_window) * 100.0
    return aroon_down


def generate_signals(
    price_df: pd.DataFrame,
    aroon_window: int = 14,
    oversold_threshold: float = 10.0,
    exit_threshold: float = 50.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    aroon_down = _aroon_down(low, aroon_window)
    entry = (aroon_down < oversold_threshold).fillna(False)
    exit_signal = (aroon_down > exit_threshold).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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

"""Strategy: Pring's Special K signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-107),
sourced from:
  - Google AI-overview synthesis of Pring's Special K trading rules:
    "Bullish: Buy or go long when the Special K line crosses above its
    signal line (typically a 100-period simple moving average of the
    indicator). Bearish: Sell or exit when the Special K line crosses below
    its signal line."
  - https://chartschool.stockcharts.com/.../prings-special-k (StockCharts
    ChartSchool): "It is normal to run a moving average through the Special
    K. The default is a 100-day smoothed by a 100-day SMA. Crossovers of the
    average typically signal a reversal in the direction of the primary
    trend." Also documents at least 725 data points required to compute
    accurately.
  - LuxAlgo / TradingView search-snippet formula: SpecialK = SMA(ROC(10),10)*1
    + SMA(ROC(15),10)*2 + SMA(ROC(20),10)*3 + SMA(ROC(30),15)*4 +
    SMA(ROC(40),50)*1 + SMA(ROC(65),65)*2 + SMA(ROC(75),75)*3 + ... (longer
    legs continue at periods 100/195/265/390/530 with the weight pattern
    repeating 4,1,2,3). This implementation uses the full 12-leg canonical
    formula (Martin Pring's original weighted sum of SMA-smoothed
    rate-of-change values across 4 nested cycles: short/intermediate/
    long/very-long term), matching the widely-published Special K
    coefficients.

First Special-K strategy in this repo -- distinct from the already-tested
KST (Know Sure Thing, 2026-09-04-057/2026-09-06-100), which is Pring's
earlier and much simpler 4-leg (10/15/20/30-period ROC) indicator. Special K
combines many more ROC legs (10 through 530-period) specifically to capture
the four-year business cycle Pring designed it around.

Signal logic
------------
- SpecialK[t] = weighted sum of SMA-smoothed ROC legs (see _special_k below).
- Signal[t] = SMA(SpecialK, signal_window)[t] (source default 100).
- Long entry: SpecialK crosses above Signal.
- Exit: SpecialK crosses back below Signal, or a max_hold_days time-stop
  (repo standard safety valve; source gives no explicit stop-loss/time-stop
  rule of its own).

Data-length caveat: the source states >=725 daily bars are needed for a
fully accurate long-cycle reading (390/530-period ROC legs need that much
history just to start). This repo's typical backtest windows (2018-2026,
~2000 daily bars) comfortably clear that bar, but very short data windows
will produce all-NaN longest-leg values (handled gracefully via
`min_periods` — those legs simply contribute 0 until enough history exists).

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


# Canonical Pring Special K legs: (roc_period, sma_window, weight)
_SPECIAL_K_LEGS = [
    (10, 10, 1),
    (15, 10, 2),
    (20, 10, 3),
    (30, 15, 4),
    (40, 50, 1),
    (65, 65, 2),
    (75, 75, 3),
    (100, 100, 4),
    (195, 130, 1),
    (265, 130, 2),
    (390, 130, 3),
    (530, 195, 4),
]


def _special_k(close: pd.Series) -> pd.Series:
    total = pd.Series(0.0, index=close.index)
    for roc_period, sma_window, weight in _SPECIAL_K_LEGS:
        roc = close.pct_change(roc_period) * 100.0
        smoothed = roc.rolling(sma_window, min_periods=sma_window).mean()
        total = total.add(smoothed.fillna(0.0) * weight, fill_value=0.0)
    return total


def generate_signals(
    price_df: pd.DataFrame,
    signal_window: int = 100,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    special_k = _special_k(close)
    signal = special_k.rolling(signal_window, min_periods=signal_window).mean()

    crossed_up = (special_k > signal) & (special_k.shift(1) <= signal.shift(1))
    crossed_down = (special_k < signal) & (special_k.shift(1) >= signal.shift(1))

    entry_arr = crossed_up.fillna(False).values
    exit_arr = crossed_down.fillna(False).values

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
    signal_window: int = 100,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(df, signal_window=signal_window, max_hold_days=max_hold_days)
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns

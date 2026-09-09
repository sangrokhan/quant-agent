"""Strategy: 200-day SMA trend filter with N-consecutive-day confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-002):
Per AllocateSmartly's "Countercyclical Trend Following" strategy writeup
(https://allocatesmartly.com/countercyclical-trend-following/), the
trend-following overlay used for SPY/GLD positions in that (much larger,
economic-regime-gated) strategy is: "If the asset closes above its 200-day
moving average for 5 consecutive days, it's in an uptrend. If it closes
below for 5 consecutive days, it's in a downtrend." AllocateSmartly's own
finding is that this trend-following overlay -- tested in isolation
against a no-trend-filter baseline -- is "key to the effectiveness of the
strategy, especially in terms of drawdown control."

This repo cannot replicate the full economic-regime-gating half of that
strategy (needs High Yield Spread and 10y/1y Treasury yield curve slope
data, not available via data/loaders.py's yfinance/ccxt-only equity/crypto
OHLCV interface -- a feasibility block, same class noted for other
macro-data-dependent candidates in this repo's log, e.g. DXY/yield-curve
entries). Instead this iteration isolates and tests the trend-following
overlay mechanism itself as a standalone long/flat strategy: is a
COUNT-based (N consecutive closes on one side) confirmation filter around
the 200-day SMA a useful trend/whipsaw filter on its own, applied directly
to the traded asset (SPY/QQQ/BTC/ETH) rather than as an allocation switch
between different assets?

This is mechanically distinct from the already-tested 2026-09-09-043
"200-SMA percent-distance hysteresis" (accepted, QQQ+SPY): that strategy's
confirmation mechanism is the MAGNITUDE of price's distance from the SMA
(a percentage band). This strategy's confirmation mechanism is instead the
DURATION price has persisted on one side (a consecutive-day count) -- a
different construction for solving the same "avoid single-bar SMA-cross
whipsaws" problem, taken directly from a different, independently-sourced
strategy writeup.

Signal logic
------------
- 200-day SMA of close.
- Track a rolling count of consecutive closes above the SMA
  (`above_streak`) and consecutive closes below the SMA (`below_streak`).
- Uptrend confirmed (long) once `above_streak >= confirm_days`.
- Downtrend confirmed (flat) once `below_streak >= confirm_days`.
- Once in a confirmed state, remain in it until the OPPOSITE state is
  confirmed (state persists through the "neutral" zone where neither
  streak has reached `confirm_days` yet -- this is the hysteresis
  behavior AllocateSmartly describes: "we maintain this above/below
  count regardless... so we always know the current trend").
- Long-only: long while in confirmed uptrend, flat while in confirmed
  downtrend or before the first confirmation of either state.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 200,
    confirm_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(sma_window, min_periods=sma_window).mean()

    above = close > sma
    below = close < sma

    above_streak = pd.Series(0, index=close.index, dtype=int)
    below_streak = pd.Series(0, index=close.index, dtype=int)
    a_run = 0
    b_run = 0
    above_vals = above.fillna(False).values
    below_vals = below.fillna(False).values
    for i in range(len(close)):
        if above_vals[i]:
            a_run += 1
        else:
            a_run = 0
        if below_vals[i]:
            b_run += 1
        else:
            b_run = 0
        above_streak.iloc[i] = a_run
        below_streak.iloc[i] = b_run

    position = pd.Series(0, index=close.index, dtype=int)
    state = 0  # 0 = flat/unconfirmed, 1 = confirmed uptrend
    for i in range(len(close)):
        if pd.isna(sma.iloc[i]):
            position.iloc[i] = 0
            continue
        if above_streak.iloc[i] >= confirm_days:
            state = 1
        elif below_streak.iloc[i] >= confirm_days:
            state = 0
        position.iloc[i] = state
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

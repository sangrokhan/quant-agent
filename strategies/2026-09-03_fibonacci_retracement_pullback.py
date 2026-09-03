"""Strategy: Fibonacci retracement pullback-buy in an uptrend, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-022),
sourced from https://www.quantifiedstrategies.com/fibonacci-trading-strategy/
(Oddmund Groette). Concrete rules quoted/paraphrased from the source: the
Fibonacci retracement tool draws horizontal levels at 23.6%, 38.2%, 50%,
61.8%, 78.6%, 100% of a preceding price swing; "many traders prefer
50%-61.8% levels" for pullback-buy entries within an established trend;
stop loss placed "beyond the 100% retracement level" (i.e. below the
swing low that started the impulse move) when entering around the
50-61.8% zone. The source's OWN documented conclusion is an explicit
negative prior: they cite Clarissa Gunawan's dissertation backtest on
Vanguard ETFs finding "the passive trading strategy outperforms the active
trading strategy using Fibonacci retracements," and state plainly "we
believe you're better off using other strategies" -- this repo tests the
concrete numeric rule anyway (50-61.8% pullback zone, uptrend filter, stop
below the swing low) as an independent falsification/confirmation check on
this repo's own QQQ/SPY/BTC/ETH universe, following the same pattern as
the Bollinger Band squeeze test (2026-09-03-011), which also started from
a documented negative prior.

Signal logic (daily bars, causal/no look-ahead):
1. Uptrend filter: close > SMA(trend_window) (default 200d).
2. Identify the most recent `swing_lookback`-day rolling high (impulse
   swing high) and the rolling low that preceded it within the same
   window (impulse swing low) -- the impulse leg is (swing_low ->
   swing_high).
3. Compute the retracement fraction of the CURRENT close back from the
   swing high toward the swing low: retracement = (swing_high - close) /
   (swing_high - swing_low).
4. Long entry when retracement is within [retrace_low, retrace_high]
   (default 0.5-0.618, the source's stated preferred zone) AND the
   uptrend filter holds.
5. Exit either when price makes a new `swing_lookback`-day high (breaks
   above the impulse swing high -- the pullback resolved bullishly as
   expected) OR when retracement exceeds 1.0 (price broke below the
   swing low -- the "stop beyond the 100% retracement level" the source
   describes), whichever comes first.

Interface contract for validators (see validation/validators.py) and grid_test.py:
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


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    swing_lookback: int = 40,
    retrace_low: float = 0.5,
    retrace_high: float = 0.618,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    swing_high = close.rolling(swing_lookback).max()
    swing_low = close.rolling(swing_lookback).min()
    swing_range = (swing_high - swing_low).replace(0.0, np.nan)
    retracement = (swing_high - close) / swing_range

    entry_zone = (retracement >= retrace_low) & (retracement <= retrace_high)
    entry_signal = (entry_zone & uptrend).fillna(False).values

    close_v = close.values
    swing_high_v = swing_high.values
    retracement_v = retracement.values

    position = np.zeros(n, dtype=int)
    in_pos = False
    for t in range(n):
        if not in_pos and entry_signal[t]:
            in_pos = True
        if in_pos:
            position[t] = 1
            # exit: new swing high (breakout resolved) or stop (retrace > 1.0)
            broke_high = not np.isnan(swing_high_v[t]) and close_v[t] >= swing_high_v[t]
            stopped_out = not np.isnan(retracement_v[t]) and retracement_v[t] > 1.0
            if broke_high or stopped_out:
                in_pos = False

    return pd.Series(position, index=close.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

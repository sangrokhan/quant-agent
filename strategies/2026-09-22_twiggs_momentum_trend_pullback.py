"""Strategy: Twiggs Momentum Oscillator (EMA-smoothed ROC) trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-007):
Per MarketCalls' disclosed trading rules
(https://www.marketcalls.in/sensex/twiggs-momentum-oscillator-for-sensex.html)
for Colin Twiggs' Momentum Oscillator (IncredibleCharts, described there as
"a smoothed version of the Rate Of Change oscillator" -- exact proprietary
formula not disclosed by any free source found this iteration, so
implemented here as the standard EMA-smoothed ROC construction that
IncredibleCharts' own description points to): identify trend direction via
price vs a 63-day EMA; in an established uptrend (price above EMA(63)), go
long when the oscillator (EMA-smoothed rate-of-change) turns upward after
dipping toward/below zero -- a "reversal within trend" pullback-continuation
entry, not a raw crossover. First test of Twiggs Momentum in this repo (0
prior KB hits).

Signal logic
------------
- Twiggs Momentum = EMA(ROC(close, roc_window), ema_window), where
  ROC(close, n) = 100 * (close / close.shift(n) - 1).
- Trend filter: close > EMA(close, trend_window).
- Long entry: trend filter true AND oscillator was below its own
  reversal_threshold (near/below zero) on the prior bar AND has just ticked
  up (oscillator[t] > oscillator[t-1]).
- Exit: trend filter turns false (close crosses below EMA(trend_window)),
  OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _twiggs_momentum(close: pd.Series, roc_window: int, ema_window: int) -> pd.Series:
    roc = 100.0 * (close / close.shift(roc_window) - 1.0)
    return roc.ewm(span=ema_window, adjust=False).mean()


def generate_signals(
    price_df: pd.DataFrame,
    roc_window: int = 21,
    ema_window: int = 10,
    trend_window: int = 63,
    reversal_threshold: float = 0.0,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    osc = _twiggs_momentum(close, roc_window=roc_window, ema_window=ema_window)
    trend_ema = close.ewm(span=trend_window, adjust=False).mean()
    uptrend = close > trend_ema

    was_low = osc.shift(1) <= reversal_threshold
    ticking_up = osc > osc.shift(1)
    entry_trigger = (uptrend & was_low & ticking_up).fillna(False)
    trend_broken = (~uptrend).fillna(True)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(len(df)):
        if not in_pos:
            if bool(entry_trigger.iloc[i]):
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
        else:
            held = i - entry_idx
            if bool(trend_broken.iloc[i]) or held >= max_hold_days:
                position.iloc[i] = 0
                in_pos = False
            else:
                position.iloc[i] = 1

    return position.reindex(df.index).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    roc_window: int = 21,
    ema_window: int = 10,
    trend_window: int = 63,
    reversal_threshold: float = 0.0,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    position = generate_signals(
        price_df,
        roc_window=roc_window,
        ema_window=ema_window,
        trend_window=trend_window,
        reversal_threshold=reversal_threshold,
        max_hold_days=max_hold_days,
    )
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

"""Strategy: Single-line Hull Moving Average (HMA) mean-reversion crossunder/crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-004):
Per QuantifiedStrategies.com's own disclosed "Strategy 1" backtest
(https://www.quantifiedstrategies.com/hull-moving-average/): buy SPY at
close when close crosses BELOW the N-day Hull Moving Average, sell when
close crosses back ABOVE the same HMA. The source explicitly finds this
mean-reversion framing (Strategy 1) outperforms the opposite momentum
framing (Strategy 2, buy on cross ABOVE) at every tested N (5,10,25,50,
100,200) -- CAR 4.86-8.84% vs 0.8-4.62% -- with N=25 the best single
config (CAR 8.84%, MDD -30.62%).

This is the OPPOSITE direction of this repo's existing HMA crossover family
(2026-09-04-026 / 2026-09-09-013: long when close crosses ABOVE HMA, exit
below -- a momentum framing, refined via wider window sweep to hma_window
=100). This iteration explicitly tests the source's own better-performing
"buy the break BELOW the HMA" mean-reversion framing, not yet present in
this repo's knowledge base.

Signal logic
------------
- Compute HMA(hma_window) per the standard Hull formula:
  HMA(n) = WMA(2*WMA(price, n/2) - WMA(price, n), round(sqrt(n)))
- Entry (long): close crosses from >= HMA to < HMA (crosses below).
- Exit: close crosses back from <= HMA to > HMA (crosses above), OR a
  max_hold_days time-stop (avoid indefinite holds during strong downtrends
  where price never reclaims the HMA).
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = np.arange(1, window + 1)

    def _w(x):
        return np.dot(x, weights) / weights.sum()

    return series.rolling(window).apply(_w, raw=True)


def _hma(series: pd.Series, window: int) -> pd.Series:
    half = max(1, int(window / 2))
    full = max(1, int(window))
    sqrt_n = max(1, int(round(np.sqrt(window))))
    wma_half = _wma(series, half)
    wma_full = _wma(series, full)
    raw = 2 * wma_half - wma_full
    return _wma(raw, sqrt_n)


def generate_signals(
    price_df: pd.DataFrame,
    hma_window: int = 15,
    max_hold_days: int = 8,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    hma = _hma(close, hma_window)

    below = close < hma
    prev_below = below.shift(1).fillna(False)
    cross_under = below & (~prev_below)  # entry trigger
    above = close > hma
    prev_above_or_eq = (~below.shift(1).fillna(True))
    cross_over = above & prev_below  # was below (or first bar), now above -> exit

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = -1
    idx_list = df.index
    for i in range(len(df)):
        if not in_pos:
            if bool(cross_under.iloc[i]):
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
        else:
            held = i - entry_idx
            if bool(cross_over.iloc[i]) or held >= max_hold_days:
                position.iloc[i] = 0
                in_pos = False
            else:
                position.iloc[i] = 1

    return position.reindex(df.index).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    hma_window: int = 15,
    max_hold_days: int = 8,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    position = generate_signals(price_df, hma_window=hma_window, max_hold_days=max_hold_days)
    # trade on next bar's return relative to the entry decision made at close[t]
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

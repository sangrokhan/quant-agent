"""Strategy: Ehlers Laguerre RSI zero-line (0.5) momentum-bias trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-110),
sourced from https://www.quantifiedstrategies.com/laguerre-rsi/
(QuantifiedStrategies "Laguerre RSI" article): "Using Zero Line (0.5) as
Momentum Bias: When the Laguerre RSI stays above 0.5, momentum is bullish.
Below 0.5 indicates bearish momentum. This simple rule can be used as a
filter for systematic strategies." Gamma parameter guidance from the same
source: "0.2: Very fast... 0.5: Balanced, widely used default... 0.7-0.8:
Smooth and slow."

Distinct from the already-tested and rejected Laguerre RSI mean-reversion
variant in this repo (2026-09-05-053, entry/exit at 0.2/0.8 thresholds) --
this iteration operationalizes the SAME underlying Laguerre RSI oscillator
but as a much simpler standalone zero-line (0.5) momentum-bias regime
signal instead of an extreme-threshold mean-reversion trigger, per the
source's own explicitly stated alternate usage pattern. Also distinct from
the Adaptive Laguerre Filter (2026-09-05-058), which is a DIFFERENT Ehlers
indicator (a price smoother, not an RSI-style oscillator).

Laguerre filter (4-stage recursive, per Ehlers' original design):
    L0[t] = (1-gamma)*price[t] + gamma*L0[t-1]
    L1[t] = -gamma*L0[t] + L0[t-1] + gamma*L1[t-1]
    L2[t] = -gamma*L1[t] + L1[t-1] + gamma*L2[t-1]
    L3[t] = -gamma*L2[t] + L2[t-1] + gamma*L3[t-1]
Laguerre RSI (CU = cumulative up, CD = cumulative down across the 4 stages'
pairwise differences):
    CU = sum of positive (L{i}-L{i+1}) pairs; CD = sum of negative pairs
    LRSI = CU / (CU + CD)  (0..1 oscillator)

Signal logic
------------
- Long entry (position=1): LRSI > 0.5 (bullish momentum bias).
- Flat (position=0): LRSI <= 0.5 (bearish momentum bias).
- No discrete entry/exit trigger or time-stop needed -- position directly
  tracks the zero-line regime state each bar (per source's own framing as a
  continuous "filter", not a discrete trade trigger), matching this repo's
  existing continuous-regime-gate convention (e.g. 2026-09-06_hvr_expansion_longonly.py).

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


def _laguerre_rsi(close: pd.Series, gamma: float) -> pd.Series:
    price = close.values
    n = len(price)
    l0 = np.zeros(n)
    l1 = np.zeros(n)
    l2 = np.zeros(n)
    l3 = np.zeros(n)
    lrsi = np.full(n, np.nan)

    for t in range(n):
        if t == 0:
            l0[t] = price[t]
            l1[t] = price[t]
            l2[t] = price[t]
            l3[t] = price[t]
            continue
        l0[t] = (1 - gamma) * price[t] + gamma * l0[t - 1]
        l1[t] = -gamma * l0[t] + l0[t - 1] + gamma * l1[t - 1]
        l2[t] = -gamma * l1[t] + l1[t - 1] + gamma * l2[t - 1]
        l3[t] = -gamma * l2[t] + l2[t - 1] + gamma * l3[t - 1]

        cu = 0.0
        cd = 0.0
        pairs = [(l0[t], l1[t]), (l1[t], l2[t]), (l2[t], l3[t])]
        for a, b in pairs:
            diff = a - b
            if diff >= 0:
                cu += diff
            else:
                cd += -diff
        if (cu + cd) != 0:
            lrsi[t] = cu / (cu + cd)
        else:
            lrsi[t] = 0.5

    return pd.Series(lrsi, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    gamma: float = 0.5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    lrsi = _laguerre_rsi(close, gamma)
    position = (lrsi > 0.5).fillna(False).astype(int)
    position.name = "position"
    return position


def generate_returns(
    price_df: pd.DataFrame,
    gamma: float = 0.5,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(df, gamma=gamma)
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns

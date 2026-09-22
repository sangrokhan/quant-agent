"""Strategy: 3-horizon weighted composite momentum with absolute-momentum cash gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-040):
Per Travis Giffin's description of the AllocateSmartly "Optimum 3" / Financial
Mentor TAA model (https://travisgiffin.com/my-allocatesmartly-tactical-asset-
allocation-2025-2026/, read via browser_exec since web_extract's DDGS backend
cannot fetch article bodies), the model's disclosed core mechanic (the
author's own reconstruction, not the proprietary weights) is:

    Score = w1*Return(3mo) + w2*Return(6mo) + w3*Return(12mo)
    If Score <= 0: go to cash (absolute momentum gate)
    Else: stay invested (weight proportional or full exposure)

This is a composite (BLENDED, 3-horizon) absolute-momentum trend/cash-switch
rule, distinct from prior repo entries: 2026-09-22-032's "blended momentum"
used only 2 horizons (not 3) plus a separate realized-vol crash-brake
mechanism (no vol brake here -- pure composite-momentum gate); Coppock Curve
entries (2026-09-14-171/2026-09-16-088) use a WMA-smoothed dual-ROC
oscillator as a continuous sizing dial layered UNDER an SMA trend gate, not
a raw 3-horizon weighted-return absolute-momentum switch. This is the first
strategy in this repo implementing the specific 3mo/6mo/12mo weighted-blend
absolute-momentum single-asset gate described by that source.

Signal logic
------------
- Score_t = w3*R(63d) + w6*R(126d) + w12*R(252d), where R(n) is the simple
  trailing n-trading-day return (approximating 3/6/12 calendar months).
- Go long (weight 1.0) when Score_t > 0; go to cash (weight 0.0) otherwise.
- Rebalanced monthly (every `rebalance_days` trading days), matching the
  source's "at each monthly rebalance" cadence -- the score is evaluated
  and position held fixed between rebalance dates to keep turnover modest
  and match the TAA-style monthly-tranche mechanic described.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df) -> pd.Series
    generate_signals(price_df) -> pd.Series  (0/1 position series)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _composite_signal(
    price_df: pd.DataFrame,
    w3: float = 1.0,
    w6: float = 1.0,
    w12: float = 1.0,
    lb3: int = 63,
    lb6: int = 126,
    lb12: int = 252,
    rebalance_days: int = 21,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    r3 = close.pct_change(lb3)
    r6 = close.pct_change(lb6)
    r12 = close.pct_change(lb12)

    wsum = w3 + w6 + w12
    score = (w3 * r3 + w6 * r6 + w12 * r12) / wsum

    raw_signal = (score > 0).astype(int)

    # Monthly rebalance: only update the held position every rebalance_days
    # trading days; hold the last decision fixed in between.
    n = len(df)
    positions = pd.Series(0, index=df.index, dtype=int)
    held = 0
    for i in range(n):
        if i % rebalance_days == 0:
            if pd.notna(score.iloc[i]):
                held = int(raw_signal.iloc[i])
        positions.iloc[i] = held

    # No position until enough history exists for the longest lookback.
    positions.iloc[: lb12] = 0
    return positions.fillna(0).astype(int)


def generate_signals(
    price_df: pd.DataFrame,
    w3: float = 1.0,
    w6: float = 1.0,
    w12: float = 1.0,
    lb3: int = 63,
    lb6: int = 126,
    lb12: int = 252,
    rebalance_days: int = 21,
) -> pd.Series:
    return _composite_signal(
        price_df,
        w3=w3,
        w6=w6,
        w12=w12,
        lb3=lb3,
        lb6=lb6,
        lb12=lb12,
        rebalance_days=rebalance_days,
    )


def generate_returns(
    price_df: pd.DataFrame,
    w3: float = 1.0,
    w6: float = 1.0,
    w12: float = 1.0,
    lb3: int = 63,
    lb6: int = 126,
    lb12: int = 252,
    rebalance_days: int = 21,
) -> pd.Series:
    df = _prep(price_df)
    positions = generate_signals(
        df,
        w3=w3,
        w6=w6,
        w12=w12,
        lb3=lb3,
        lb6=lb6,
        lb12=lb12,
        rebalance_days=rebalance_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    # Position held from t-1 applied to t's return (avoid lookahead).
    strat_ret = positions.shift(1).fillna(0) * daily_ret
    return strat_ret

"""Strategy: Lag-3 directional-reversal (Fourier-Residue Identity sign channel).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-013):
Per Victoria Portnaya's "The Bounce Has No Direction: Sign, Magnitude, and
the Microstructure of Equity Return Predictability" (arXiv:2606.29591,
https://arxiv.org/abs/2606.29591, visited this iteration): the paper
decomposes SPY's return autocorrelation via a Fourier-Residue Identity
(FRI) into an independent sign (directional reversal) channel and a
magnitude (volatility-clustering/bid-ask-bounce) channel. Its key finding
distinct from lag-1 (which the paper shows is driven ENTIRELY by magnitude
shrinkage, not direction -- "the FRI sign test is insignificant (p=0.11)"
at lag 1) is that "At lag 3, a significant directional reversal (p=0.02)
invisible to the scalar ACF reveals a separate partial-price-adjustment
channel."

This is operationalized here as a genuine DIRECTIONAL reversal signal at
lag 3 specifically (not lag 1, which this repo's prior autocorrelation
entry 2026-09-08-121 already tested and found no edge in as a REGIME-SWITCH
mechanism, not a direct trading trigger): a down day 3 trading days ago
predicts a partial upward price-adjustment today. Long entry when the
3-day-lagged daily return was negative (below -reversal_threshold, default
0.0 i.e. any negative lagged return); exit after a short fixed hold
(hold_days, default 1-3 days, since the paper's "partial-price-adjustment"
framing implies a short-lived correction, not a persistent trend), or
immediately if signal_only mode requires no lagged-return condition is
active this bar.

Distinct from 2026-09-08-121 (lag-1 ACF SIGN used as a regime-SWITCHER
between momentum/mean-reversion trading modes, rejected) because: (1) this
uses lag-3, the specific lag the paper identifies as having a genuine
directional-reversal signature (lag-1 in the paper is magnitude-only, no
directional edge -- consistent with why 2026-09-08-121's lag-1 approach
found nothing), and (2) this is a direct fixed-hold reversal TRADE trigger,
not a regime classifier gating a separate trend/reversion sub-strategy.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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
    reversal_lag: int = 3,
    reversal_threshold: float = 0.0,
    hold_days: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    daily_ret = close.pct_change()
    lagged_ret = daily_ret.shift(reversal_lag)

    entry = lagged_ret < -reversal_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if pd.notna(entry.iloc[i]) else False:
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

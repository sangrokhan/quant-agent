"""Strategy: Chande Momentum Oscillator (CMO) oversold-bounce with short time-stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-074):
Per QuantifiedStrategies.com's "Chande Momentum Oscillator Trading Strategy"
(https://www.quantifiedstrategies.com/chande-momentum-oscillator-trading-strategy/),
the CMO (Tushar Chande, 1994, "The New Technical Trader") is a momentum
oscillator ranging -100..+100, symmetric around zero, with disclosed
overbought/oversold thresholds of +50/-50. The article's own SPY backtest
(numeric entry/exit rules paywalled, but summary stats + methodology
disclosed) found a 5-day maximum holding period outperformed 10/15/30-day
holds monotonically -- CAGR 4.19% vs buy-and-hold 9.90%, but risk-adjusted
return 26.80% (CAGR/time-in-market 15.63%) beat buy-and-hold on a
risk-adjusted basis, with a much smaller max drawdown (-34.63% vs -55.19%
buy-and-hold). This entry independently constructs and tests a concrete
oversold-bounce hypothesis using the disclosed period/threshold/hold-period
findings: long when CMO(9) crosses below -50 (extreme oversold), held for
exactly max_hold_days=5 trading days or an early exit if CMO recovers above
0 first (whichever comes first) -- distinct from the paywalled exact rule,
but grounded in the article's own disclosed parameters and its finding that
short holds beat long ones. 0 prior bare-CMO-as-primary-signal entries in
this repo (VIDYA, 2026-09-20-073, uses CMO only internally as an adaptive
smoothing weight, a structurally different application).

CMO formula (Chande, standard):
    SHc = sum of positive daily closing-price changes over `period`
    SLc = sum of |negative daily closing-price changes| over `period`
    CMO = 100 * (SHc - SLc) / (SHc + SLc)

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _cmo(close: pd.Series, period: int = 9) -> pd.Series:
    diff = close.diff()
    up = diff.clip(lower=0.0)
    down = (-diff).clip(lower=0.0)
    up_sum = up.rolling(period).sum()
    down_sum = down.rolling(period).sum()
    denom = (up_sum + down_sum).replace(0, np.nan)
    cmo = 100.0 * (up_sum - down_sum) / denom
    return cmo


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 9,
    oversold_threshold: float = -50.0,
    recovery_threshold: float = 0.0,
    max_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry when CMO(period) crosses below `oversold_threshold` (extreme
    oversold bounce entry). Exit on whichever comes first: CMO recovering
    above `recovery_threshold`, or `max_hold_days` trading days elapsed
    (per the source's own disclosed finding that short holds outperform
    long ones for this oscillator).
    """
    df = _prep(price_df)
    close = df["close"]
    cmo = _cmo(close, period=period)

    oversold_cross = (cmo < oversold_threshold) & (cmo.shift(1) >= oversold_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_count = 0
    cmo_vals = cmo.values
    oversold_cross_vals = oversold_cross.values

    for i in range(len(close)):
        if in_position:
            hold_count += 1
            recovered = (not np.isnan(cmo_vals[i])) and cmo_vals[i] > recovery_threshold
            if recovered or hold_count >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                hold_count = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(oversold_cross_vals[i]):
                in_position = True
                hold_count = 0
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

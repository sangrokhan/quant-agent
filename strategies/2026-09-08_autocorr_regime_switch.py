"""Strategy: Adaptive Momentum/Mean-Reversion via rolling lag-1 return autocorrelation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-121):
Per https://blog.quantinsti.com/autocorrelation/ (general autocorrelation-
in-trading concept): "positive autocorrelation suggests short-term momentum
or trend-following behaviour" while negative lag-1 autocorrelation of
returns implies mean-reverting behavior. Rather than assuming one regime
applies always, this strategy computes the ROLLING lag-1 autocorrelation of
daily returns over a trailing window and SWITCHES strategy logic based on
its sign: when rolling autocorrelation is positive (momentum regime), go
long if the recent N-day return is positive (trend-following); when rolling
autocorrelation is negative (mean-reversion regime), go long if the most
recent day's return was negative (buy the dip). This is the first
autocorrelation-regime-adaptive strategy in this repo -- distinct from
static momentum or mean-reversion strategies that don't condition on
measured return persistence/reversal strength.

Signal logic
------------
- Daily log returns.
- rolling_autocorr: lag-1 autocorrelation of daily returns over a trailing
  `acf_window` (default 60) days.
- Momentum regime (rolling_autocorr > acf_threshold): long when the
  trailing `mom_lookback`-day cumulative return > 0.
- Mean-reversion regime (rolling_autocorr < -acf_threshold): long when
  yesterday's daily return < 0 (buy the dip), held for `mr_hold_days`.
- Neutral zone (|rolling_autocorr| <= acf_threshold): flat (no
  edge/inconclusive regime).
- Long-only, one position at a time.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _lag1_autocorr(x: np.ndarray) -> float:
    if len(x) < 3:
        return 0.0
    a, b = x[:-1], x[1:]
    if a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def generate_signals(
    price_df: pd.DataFrame,
    acf_window: int = 60,
    acf_threshold: float = 0.1,
    mom_lookback: int = 10,
    mr_hold_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else 0.0).astype(float)

    rolling_acf = daily_log_ret.rolling(acf_window).apply(_lag1_autocorr, raw=True)
    mom_cum_ret = close.pct_change(mom_lookback)
    prev_day_ret = daily_log_ret.shift(1)  # yesterday's return, known at today's open

    momentum_regime = rolling_acf > acf_threshold
    reversion_regime = rolling_acf < -acf_threshold

    mom_entry = momentum_regime & (mom_cum_ret.shift(1) > 0)
    mr_entry = reversion_regime & (prev_day_ret < 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    in_mr_trade = False
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if in_mr_trade:
                if held >= mr_hold_days:
                    in_position = False
                    position.iloc[i] = 0
                    continue
                position.iloc[i] = 1
            else:
                # momentum trade: stay in as long as still in momentum regime and trend positive
                if not bool(momentum_regime.iloc[i]) or not bool(mom_cum_ret.iloc[i] > 0):
                    in_position = False
                    position.iloc[i] = 0
                    continue
                position.iloc[i] = 1
        else:
            if bool(mr_entry.iloc[i]):
                in_position = True
                in_mr_trade = True
                entry_idx = i
                position.iloc[i] = 1
            elif bool(mom_entry.iloc[i]):
                in_position = True
                in_mr_trade = False
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

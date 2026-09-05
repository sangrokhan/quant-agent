"""Strategy: Ehlers Laguerre RSI mean-reversion (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-053):
John Ehlers' Laguerre RSI applies a 4-stage low-lag Laguerre filter (governed
by a single gamma smoothing parameter) to RSI-style up/down accumulation,
producing a smoother 0-1 oscillator with less whipsaw than classic RSI.
Per quantifiedstrategies.com's own stated "research-friendly" mean-reversion
rule: go long when Laguerre RSI crosses UP through a low oversold threshold
(0.2) after having been below it, and exit when Laguerre RSI crosses UP
through a high overbought threshold (0.8) (their SPY 1993-2026 backtest:
519 trades, 61% win rate, 21% max DD, ~12% time invested). This is distinct
from every previously-tested oscillator-threshold strategy in this repo
(Connors RSI composite, CCI, Williams %R, Fisher Transform, DeMarker, etc.)
because the Laguerre filter itself (L0..L3 recursive smoothing via gamma,
not a fixed-length rolling window) is a categorically different smoothing
mechanism never tried here before.

Signal logic
------------
- Compute the 4-stage Laguerre filter of price (L0, L1, L2, L3) using
  smoothing parameter `gamma` (0 < gamma < 1).
- Laguerre RSI = (CU) / (CU + CD) where CU/CD are cumulative up/down moves
  across the successive filtered levels (L0->L1, L1->L2, L2->L3).
- Entry (long): Laguerre RSI crosses UP through `entry_level` (e.g. 0.2)
  having been below it the prior bar.
- Exit: Laguerre RSI crosses UP through `exit_level` (e.g. 0.8), OR a
  max_hold_days time-stop (avoid indefinite holds during a Laguerre RSI that
  drifts sideways just above entry_level without ever reaching exit_level).
- Flat (no position) otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _laguerre_rsi(price: pd.Series, gamma: float) -> pd.Series:
    """Ehlers' 4-stage Laguerre filter applied to price, then RSI-style
    up/down accumulation across the filtered levels -> oscillator in [0,1].
    """
    n = len(price)
    l0 = np.zeros(n)
    l1 = np.zeros(n)
    l2 = np.zeros(n)
    l3 = np.zeros(n)
    lrsi = np.zeros(n)
    p = price.to_numpy(dtype=float)

    for i in range(n):
        if i == 0 or np.isnan(p[i]):
            l0[i] = p[i] if not np.isnan(p[i]) else 0.0
            l1[i] = l0[i]
            l2[i] = l0[i]
            l3[i] = l0[i]
        else:
            l0[i] = (1 - gamma) * p[i] + gamma * l0[i - 1]
            l1[i] = -gamma * l0[i] + l0[i - 1] + gamma * l1[i - 1]
            l2[i] = -gamma * l1[i] + l1[i - 1] + gamma * l2[i - 1]
            l3[i] = -gamma * l2[i] + l2[i - 1] + gamma * l3[i - 1]

        cu = 0.0
        cd = 0.0
        if l0[i] >= l1[i]:
            cu += l0[i] - l1[i]
        else:
            cd += l1[i] - l0[i]
        if l1[i] >= l2[i]:
            cu += l1[i] - l2[i]
        else:
            cd += l2[i] - l1[i]
        if l2[i] >= l3[i]:
            cu += l2[i] - l3[i]
        else:
            cd += l3[i] - l2[i]

        if (cu + cd) != 0:
            lrsi[i] = cu / (cu + cd)
        else:
            lrsi[i] = lrsi[i - 1] if i > 0 else 0.5

    return pd.Series(lrsi, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    gamma: float = 0.5,
    entry_level: float = 0.2,
    exit_level: float = 0.8,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    lrsi = _laguerre_rsi(close, gamma)

    below_entry = lrsi < entry_level
    was_below_entry = below_entry.shift(1).fillna(False)
    entry_cross = (lrsi >= entry_level) & was_below_entry

    below_exit = lrsi < exit_level
    was_below_exit = below_exit.shift(1).fillna(True)
    exit_cross = (lrsi >= exit_level) & was_below_exit

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(close)):
        if not in_pos:
            if entry_cross.iloc[i]:
                in_pos = True
                hold_count = 0
        else:
            hold_count += 1
            if exit_cross.iloc[i] or hold_count >= max_hold_days:
                in_pos = False
        position.iloc[i] = 1 if in_pos else 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    gamma: float = 0.5,
    entry_level: float = 0.2,
    exit_level: float = 0.8,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        gamma=gamma,
        entry_level=entry_level,
        exit_level=exit_level,
        max_hold_days=max_hold_days,
    )
    # trade on next bar's return relative to signal formed at close of prior bar
    strat_returns = position.shift(1).fillna(0) * daily_ret
    return strat_returns

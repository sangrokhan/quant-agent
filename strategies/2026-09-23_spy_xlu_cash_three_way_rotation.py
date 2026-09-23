"""Strategy: SPY/XLU/cash three-way rotation (rescue of 2026-09-23-151).

Hypothesis (direct follow-up to this cron trigger's own near-decisive
rejection, id=2026-09-23-151 -- Weekly SPY vs XLU relative-performance
rotation, per QuantifiedStrategies.com's "Weekly Rotating System Between
S&P 500 And Utilities"): the parent strategy's decisive MDD failure (0.367
vs 0.25) was explicitly diagnosed as structural -- being ALWAYS fully
invested in one of {SPY, XLU} with no cash state meant it never de-risked
during genuine systemic drawdowns (2020 COVID, 2022 bear) where both assets
fell together. This iteration adds a THIRD rotation option: cash (flat),
selected whenever NEITHER asset has a positive trailing lookback_days
return (i.e. both are losing money over the lookback window -- a cheap,
single-symbol-computable proxy for "systemic risk-off", not requiring any
new data source). Otherwise, hold whichever of SPY/XLU has the better
trailing return, exactly as the parent strategy did. This directly tests
whether adding a genuine flat/cash state (rather than forced full
investment) rescues the MDD failure while preserving the underlying
relative-performance-rotation edge.

Signal logic
------------
- Same trailing lookback_days return computation for underlying (price_df's
  own asset) and XLU as the parent strategy, refreshed every
  rebalance_days bars.
- If BOTH trailing returns are <= 0: hold CASH (flat, position=0 on both).
- Else: hold whichever of the two has the higher trailing return (as
  before).

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5/6):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position on the
        UNDERLYING (price_df's own asset); 1 = hold underlying, 0 = hold
        either XLU or cash)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns -- underlying's return while holding underlying, XLU's
        return while holding XLU, 0 while in cash)
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


def _load_xlu(start, end) -> pd.Series:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    xlu_df = load_equity("XLU", start, end)
    xlu_df = xlu_df.set_index("timestamp") if "timestamp" in xlu_df.columns else xlu_df
    return xlu_df.sort_index()["close"]


def _decide_states(
    price_df: pd.DataFrame,
    lookback_days: int,
    rebalance_days: int,
    cash_trigger: str = "both",
) -> np.ndarray:
    """Return an array of states per bar: 1=underlying, 0=XLU, -1=cash.

    cash_trigger: "both" (original rule, cash only when BOTH trailing
    returns are non-positive) or "either" (faster de-risking rescue
    variant, cash when EITHER trailing return is non-positive -- per
    2026-09-23-152's own follow-up note).
    """
    df = _prep(price_df)
    close = df["close"]

    start = close.index.min()
    end = close.index.max()
    xlu_close = _load_xlu(start, end)
    xlu_close = xlu_close.reindex(close.index).ffill().bfill()

    underlying_trailing_ret = close.pct_change(periods=lookback_days)
    xlu_trailing_ret = xlu_close.pct_change(periods=lookback_days)

    n = len(df)
    u_ret = underlying_trailing_ret.to_numpy()
    x_ret = xlu_trailing_ret.to_numpy()
    states = np.zeros(n, dtype=int)
    current = 1
    for i in range(n):
        if i % rebalance_days == 0:
            u = u_ret[i]
            x = x_ret[i]
            if np.isnan(u) or np.isnan(x):
                current = 1
            elif cash_trigger == "either" and (u <= 0 or x <= 0):
                current = -1  # cash
            elif cash_trigger == "both" and (u <= 0 and x <= 0):
                current = -1  # cash
            elif u >= x:
                current = 1  # underlying
            else:
                current = 0  # xlu
        states[i] = current
    return states


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 20,
    rebalance_days: int = 5,
    cash_trigger: str = "both",
) -> pd.Series:
    """Return a {0,1} series: 1 = hold underlying, 0 = hold XLU or cash."""
    df = _prep(price_df)
    states = _decide_states(price_df, lookback_days, rebalance_days, cash_trigger)
    pos = (states == 1).astype(int)
    return pd.Series(pos, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    lookback_days: int = 20,
    rebalance_days: int = 5,
    cash_trigger: str = "both",
) -> pd.Series:
    """Daily strategy returns: underlying's return / XLU's return / 0 (cash)."""
    df = _prep(price_df)
    close = df["close"]

    start = close.index.min()
    end = close.index.max()
    xlu_close = _load_xlu(start, end)
    xlu_close = xlu_close.reindex(close.index).ffill().bfill()

    states = _decide_states(price_df, lookback_days, rebalance_days, cash_trigger)
    states_shifted = np.roll(states, 1)
    states_shifted[0] = 1

    underlying_daily_ret = close.pct_change().fillna(0.0).to_numpy()
    xlu_daily_ret = xlu_close.pct_change().fillna(0.0).to_numpy()

    strat_ret = np.where(
        states_shifted == 1, underlying_daily_ret,
        np.where(states_shifted == 0, xlu_daily_ret, 0.0),
    )
    return pd.Series(strat_ret, index=df.index)

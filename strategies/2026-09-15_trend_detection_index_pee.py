"""Strategy: Trend Detection Index (TDI, M.H. Pee) trend/consolidation
regime + Direction Indicator crossover, long-only.

Hypothesis (knowledge_base id 2026-09-15-110):
Per Linn Software's Investor/RT documentation
(https://www.linnsoft.com/techind/trend-detection-index-tdi), the Trend
Detection Index distinguishes trending markets from consolidating ones
using only price momentum: let mom = close - close(n days ago). TDI =
sum(|mom|, n) - |sum(mom, n)| over a rolling n-day window (positive TDI =
trending, since absolute momentum sums to more than the net directional
momentum only when price has moved back and forth -- wait, actually the
opposite: TDI is LOW/negative when price has been moving persistently in
one direction, since sum(|mom|) ~= |sum(mom)| in a clean trend, and TDI is
HIGH when momentum has been choppy/oscillating. Source's own stated rule:
"TDI will signal a trend if it shows a positive value and a consolidation
if it shows a negative value" -- so despite the naive formula's
counter-intuitive-looking construction, we follow the source's own
disclosed direction/threshold verbatim rather than second-guessing it.
Direction Indicator = sum(mom, n) over the same window (positive =
uptrend, negative = downtrend). Source's own entry rule: "Enter long
tomorrow at the open if both the TDI and direction indicator are positive
after today's close." First Trend Detection Index (Pee) entry in this
repo -- 0 prior matches (not to be confused with the unrelated "Traders
Dynamic Index" which shares the TDI acronym and has several prior entries
in this repo already).

Source: https://www.linnsoft.com/techind/trend-detection-index-tdi

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _tdi_and_direction(close: pd.Series, momentum_period: int, tdi_period: int):
    mom = close.diff(momentum_period)
    abs_mom_sum = mom.abs().rolling(tdi_period).sum()
    mom_sum = mom.rolling(tdi_period).sum()
    tdi = abs_mom_sum - mom_sum.abs()
    direction = mom_sum
    return tdi, direction


def generate_signals(
    price_df: pd.DataFrame,
    momentum_period: int = 20,
    tdi_period: int = 20,
    max_hold_days: int = 40,
) -> pd.Series:
    """Long-only: enter (next-bar semantics handled by generate_returns'
    shift) when TDI > 0 (source's "trending" regime) AND the Direction
    Indicator > 0 (uptrend); exit when either condition breaks or after
    max_hold_days.
    """
    df = _prep(price_df)
    close = df["close"]

    tdi, direction = _tdi_and_direction(close, momentum_period, tdi_period)
    long_condition = (tdi > 0) & (direction > 0)
    long_condition = long_condition.fillna(False)

    position = pd.Series(0.0, index=close.index)
    in_position = False
    bars_held = 0
    vals = long_condition.to_numpy()
    pos = position.to_numpy().copy()
    for i in range(len(vals)):
        if in_position:
            bars_held += 1
            if not vals[i] or bars_held >= max_hold_days:
                in_position = False
                bars_held = 0
                pos[i] = 0.0
            else:
                pos[i] = 1.0
        else:
            if vals[i]:
                in_position = True
                bars_held = 0
                pos[i] = 1.0
            else:
                pos[i] = 0.0
    return pd.Series(pos, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    momentum_period: int = 20,
    tdi_period: int = 20,
    max_hold_days: int = 40,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        momentum_period=momentum_period,
        tdi_period=tdi_period,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret

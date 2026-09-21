"""Strategy: William Blau's Directional Trend Index (DTI) zero-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://www.mql5.com/en/code/384 and https://www.mql5.com/en/code/382
(Andrey Bolkonsky's MQL5 port of William Blau's "Momentum, Direction, and
Divergence"), the Directional Trend Index (DTI) is a normalized,
triple-EMA-smoothed Composite High/Low Momentum:

    HMU(q) = max(High - High[q-1], 0)          (up-trend momentum)
    LMD(q) = max(-(Low - Low[q-1]), 0)         (down-trend momentum)
    HLM(q) = HMU(q) - LMD(q)                   (composite High/Low momentum)
    DTI(q,r,s,u) = 100 * EMA(EMA(EMA(HLM(q),r),s),u)
                       / EMA(EMA(EMA(|HLM(q)|,r),s),u)

DTI's sign indicates trend direction by construction (positive HLM = rising
highs outpacing falling lows = uptrend), triple-smoothed to filter noise,
and normalized into a roughly [-100,100] range by the ratio-of-EMAs
construction. Per the standard interpretation shared across Blau's momentum
family (Momentum, TSI, Ergodic Oscillator -- all already tested in this
repo via zero-line-crossover or divergence signals), DTI crossing above zero
signals trend turning up. This is the FIRST Directional Trend Index / HLM
Composite High-Low Momentum strategy in this repo -- distinct from every
prior Blau-family entry (Mtm, TSI, Ergodic Oscillator, DSS) since DTI's
core input is the Composite High/Low Momentum (asymmetric up-move vs.
down-move momentum built from High/Low, not from Close), not a simple
close-to-close momentum or stochastic ratio.

Signal logic
------------
- Entry (long): DTI crosses from <=0 to >0 (default q=2,r=20,s=5,u=3, Blau's
  own defaults from the disclosed spec).
- Exit: DTI crosses back to <=0, OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and the
grid tester (see validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _triple_ema(series: pd.Series, r: int, s: int, u: int) -> pd.Series:
    e1 = series.ewm(span=r, min_periods=r, adjust=False).mean()
    e2 = e1.ewm(span=s, min_periods=s, adjust=False).mean()
    e3 = e2.ewm(span=u, min_periods=u, adjust=False).mean()
    return e3


def _dti(
    high: pd.Series,
    low: pd.Series,
    q: int = 2,
    r: int = 20,
    s: int = 5,
    u: int = 3,
) -> pd.Series:
    hmu = (high - high.shift(q - 1)).clip(lower=0.0)
    lmd = (-(low - low.shift(q - 1))).clip(lower=0.0)
    hlm = hmu - lmd

    smoothed_hlm = _triple_ema(hlm, r, s, u)
    smoothed_abs_hlm = _triple_ema(hlm.abs(), r, s, u)

    dti = 100.0 * smoothed_hlm / smoothed_abs_hlm.replace(0.0, 1e-12)
    return dti


def generate_signals(
    price_df: pd.DataFrame,
    q: int = 2,
    r: int = 20,
    s: int = 5,
    u: int = 3,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: DTI crosses from <=0 to >0.
    Exit: DTI crosses back to <=0, or max_hold_days elapsed.
    """
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]

    dti = _dti(high, low, q, r, s, u)
    above_zero = dti > 0
    cross_up = above_zero & ~above_zero.shift(1).fillna(False)
    cross_down = (~above_zero) & above_zero.shift(1).fillna(False)

    position = pd.Series(0, index=high.index, dtype=int)
    in_position = False
    entry_idx = 0
    n = len(high)
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
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

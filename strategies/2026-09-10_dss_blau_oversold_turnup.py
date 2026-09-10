"""Strategy: Double Smoothed Stochastic (DSS, William Blau) oversold
turn-up entry with a symmetric turn-down exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-XXX):
Per Wealth-Lab's DSS wiki page (visited this iteration,
http://www2.wealth-lab.com/WL5Wiki/DSS.ashx), the Double Smoothed
Stochastic (William Blau) applies two chained EMA smoothings (periods
`period1`, `period2`) to the raw Stochastic %K numerator/denominator
components BEFORE computing the ratio, producing a much smoother
oscillator than the raw Stochastic:

    HH = rolling max(high, stoch_period), LL = rolling min(low, stoch_period)
    CL = close - LL,  HL = HH - LL
    CL2 = EMA(CL, period2),  HL2 = EMA(HL, period2)
    CL1 = EMA(CL2, period1), HL1 = EMA(HL2, period1)
    DSS = 100 * CL1 / HL1

The source's OWN worked strategy example (WealthScript code in the wiki
page) is exactly: "Buy when DSS turns up from an oversold level"
(specifically: DSS crosses/turns up AND the value one bar prior to the
turn was below an oversold threshold, their example uses 24), "Sell when
DSS turns down" (symmetric turn-down exit, no separate overbought
threshold required for the exit in their example). This iteration
implements that disclosed rule directly, long-only per SAFETY.md, adding
a max_hold_days safety backstop not present in the source (which relies
purely on the symmetric turn-down exit).

First DSS/Blau-double-smoothed-stochastic strategy in this repo --
distinct from every plain Stochastic/StochRSI/StochK-divergence strategy
already tested via the double-EMA-smoothing-before-ratio construction,
which is structurally different from smoothing the %K line AFTER
computing the ratio (as %D typically does).

Signal logic
------------
- dss[t] as defined above (period1, period2, stoch_period params).
- turn_up[t] = dss[t-1] < dss[t] AND dss[t-2] >= dss[t-1] (local trough)
  AND dss[t-1] < oversold_threshold (the trough was in oversold territory).
- turn_down[t] = dss[t-1] > dss[t] AND dss[t-2] <= dss[t-1] (local peak).
- Entry (long): turn_up.
- Exit: turn_down, OR max_hold_days time-stop.

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


def _dss(df: pd.DataFrame, stoch_period: int, period1: int, period2: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    hh = high.rolling(stoch_period).max()
    ll = low.rolling(stoch_period).min()
    cl = close - ll
    hl = hh - ll

    cl2 = cl.ewm(span=period2, adjust=False).mean()
    hl2 = hl.ewm(span=period2, adjust=False).mean()
    cl1 = cl2.ewm(span=period1, adjust=False).mean()
    hl1 = hl2.ewm(span=period1, adjust=False).mean()

    dss = 100.0 * cl1 / hl1.replace(0, pd.NA)
    return dss


def generate_signals(
    price_df: pd.DataFrame,
    stoch_period: int = 13,
    period1: int = 8,
    period2: int = 5,
    oversold_threshold: float = 24.0,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    dss = _dss(df, stoch_period, period1, period2)
    dss_prev1 = dss.shift(1)
    dss_prev2 = dss.shift(2)

    turn_up = (dss_prev1 < dss) & (dss_prev2 >= dss_prev1) & (dss_prev1 < oversold_threshold)
    turn_down = (dss_prev1 > dss) & (dss_prev2 <= dss_prev1)

    entry = turn_up.fillna(False)
    exit_condition = turn_down.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_condition.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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

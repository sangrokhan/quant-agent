"""Strategy: WaveTrend Oscillator (LazyBear) crossover with overbought/oversold band gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-008):
Per LazyBear's disclosed Pine Script source for the WaveTrend Oscillator
[WT_LB] (https://github.com/bnvnvnv/fmzstrategies/blob/master/Indicator-WaveTrend-Oscillator.md,
mirroring the original TradingView page
https://www.tradingview.com/script/2KE8wTuF-Indicator-WaveTrend-Oscillator-WT/):

    ap  = (H+L+C)/3                       (typical price)
    esa = EMA(ap, n1)
    d   = EMA(|ap - esa|, n1)
    ci  = (ap - esa) / (0.015 * d)
    tci = EMA(ci, n2)
    wt1 = tci
    wt2 = SMA(wt1, 4)

The source's own strategy logic: long when wt1 crosses above the oversold
level (i.e. was below osLevel1, now recovering), short/exit when wt1
crosses above the overbought level. Long-only here (no short per SAFETY.md
scope of this repo's existing strategies): buy when wt1 crosses above wt2
WHILE below the oversold band (mean-reversion-style recovery entry), exit
when wt1 crosses back below wt2 OR climbs above the overbought band. First
test of the WaveTrend Oscillator in this repo (0 prior KB hits).

Signal logic
------------
- Long entry: wt1 crosses above wt2 (wt1[t]>wt2[t] and wt1[t-1]<=wt2[t-1])
  AND wt1[t] < os_level1 (deeply oversold recovery, per source's band
  gating).
- Exit: wt1 crosses back below wt2, OR wt1 rises above ob_level1
  (overbought, source's short-entry threshold used here as a long-exit
  signal instead), OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wavetrend(df: pd.DataFrame, n1: int, n2: int):
    ap = (df["high"] + df["low"] + df["close"]) / 3.0
    esa = ap.ewm(span=n1, adjust=False).mean()
    d = (ap - esa).abs().ewm(span=n1, adjust=False).mean()
    d_safe = d.where(d != 0, other=float("nan"))
    ci = (ap - esa) / (0.015 * d_safe)
    tci = ci.ewm(span=n2, adjust=False).mean()
    wt1 = tci
    wt2 = wt1.rolling(4).mean()
    return wt1, wt2


def generate_signals(
    price_df: pd.DataFrame,
    n1: int = 10,
    n2: int = 21,
    os_level1: float = -60.0,
    ob_level1: float = 60.0,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    wt1, wt2 = _wavetrend(df, n1=n1, n2=n2)

    cross_up = (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1))
    cross_down = (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1))
    entry_trigger = (cross_up & (wt1 < os_level1)).fillna(False)
    exit_trigger = (cross_down | (wt1 > ob_level1)).fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(len(df)):
        if not in_pos:
            if bool(entry_trigger.iloc[i]):
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
        else:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days:
                position.iloc[i] = 0
                in_pos = False
            else:
                position.iloc[i] = 1

    return position.reindex(df.index).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    n1: int = 10,
    n2: int = 21,
    os_level1: float = -60.0,
    ob_level1: float = 60.0,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    position = generate_signals(
        price_df, n1=n1, n2=n2, os_level1=os_level1, ob_level1=ob_level1,
        max_hold_days=max_hold_days,
    )
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

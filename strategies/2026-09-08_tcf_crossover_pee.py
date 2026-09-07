"""Strategy: Trend Continuation Factor (TCF, M.H. Pee) crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-027):
Per M.H. Pee's original Trend Continuation Factor (Technical Analysis of
Stocks & Commodities, Vol. 20:3, March 2001) as transcribed exactly in
ProRealCode's PRT source
(https://www.prorealcode.com/prorealtime-indicators/trend-continuation-factor/):

    r = ROC(1, close)                      # 1-bar rate of change (diff)
    pc = max(r, 0)                         # positive component
    nc = max(-r, 0)                        # negative component
    ncf = running cumulative sum of nc, RESET to 0 whenever nc==0
    pcf = running cumulative sum of pc, RESET to 0 whenever pc==0
    TCF+ = SUM(pc, sumperiod) - SUM(ncf, sumperiod)
    TCF- = SUM(nc, sumperiod) - SUM(pcf, sumperiod)

Per TradingPedia's and Linnsoft's own stated trading rules: "enter long
positions when the PlusTCF value is positive, and enter short positions
when the MinusTCF value is positive" (both cannot be positive
simultaneously; both negative = consolidation/no trend), and separately,
"traders also tend to regard the crossovers of the PlusTCF and MinusTCF
lines as entry signals in the direction of the advancing line." This
strategy implements the CROSSOVER variant (TCF+ crossing above TCF-):
distinct from a fixed-threshold rule, a crossover reacts specifically to
the *relative* momentum shift between the two components rather than an
absolute positive/negative level, which the source itself flags as the
more commonly used entry trigger among experienced traders. First TCF
strategy in this repo -- same author (M.H. Pee) as Trend Intensity Index
(2026-09-04-123, rejected), Trend Trigger Factor (2026-09-05-015, accepted
SPY only), and Random Walk Index (2026-09-04-153), but TCF's construction
(a signed-ROC dual-cumulative-summation pair, reset on sign flips) is
structurally distinct from all three.

Signal logic
------------
- Long entry: TCF+ crosses above TCF- (bullish momentum takes over).
- Exit: TCF- crosses back above TCF+ (mirror bearish cross), or a
  max_hold_days time-stop.
- Flat otherwise; long-only, matching repo convention.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py).
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


def _tcf(close: pd.Series, sumperiod: int) -> tuple[pd.Series, pd.Series]:
    """Trend Continuation Factor (TCF+, TCF-), reused exactly per
    ProRealCode's disclosed PRT source (M.H. Pee, TASC Mar 2001)."""
    r = close.diff()  # ROC[1](close), i.e. 1-bar difference
    pc = r.clip(lower=0.0).fillna(0.0)
    nc = (-r).clip(lower=0.0).fillna(0.0)

    n = len(close)
    ncf = np.zeros(n)
    pcf = np.zeros(n)
    nc_vals = nc.to_numpy()
    pc_vals = pc.to_numpy()
    for i in range(n):
        if nc_vals[i] == 0.0:
            ncf[i] = 0.0
        else:
            ncf[i] = (ncf[i - 1] if i > 0 else 0.0) + nc_vals[i]
        if pc_vals[i] == 0.0:
            pcf[i] = 0.0
        else:
            pcf[i] = (pcf[i - 1] if i > 0 else 0.0) + pc_vals[i]

    ncf_s = pd.Series(ncf, index=close.index)
    pcf_s = pd.Series(pcf, index=close.index)

    tcf_plus = pc.rolling(sumperiod).sum() - ncf_s.rolling(sumperiod).sum()
    tcf_minus = nc.rolling(sumperiod).sum() - pcf_s.rolling(sumperiod).sum()
    return tcf_plus, tcf_minus


def generate_signals(
    price_df: pd.DataFrame,
    sumperiod: int = 35,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    tcf_plus, tcf_minus = _tcf(close, sumperiod)

    bullish_cross = (tcf_plus > tcf_minus) & (tcf_plus.shift(1) <= tcf_minus.shift(1))
    bearish_cross = (tcf_minus > tcf_plus) & (tcf_minus.shift(1) <= tcf_plus.shift(1))

    valid = tcf_plus.notna() & tcf_minus.notna()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(bearish_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(bullish_cross.iloc[i]):
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

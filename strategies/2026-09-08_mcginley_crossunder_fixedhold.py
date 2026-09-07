"""Strategy: McGinley Dynamic price-crossunder mean reversion, fixed N-day hold.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-020):
Per QuantifiedStrategies.com's own disclosed McGinley Dynamic backtest
(https://www.quantifiedstrategies.com/mcginley-dynamic/, SPY, several MD
periods tested): "when the close of SPY crosses BELOW the N-day [McGinley
Dynamic] average, we buy SPY at the close... sell after N-days" is the
source's own "Strategy 3" -- their own results table shows SHORT McGinley
periods (5-25 days) work best for this mean-reversion variant, with average
gain-per-trade increasing as the FIXED HOLD period lengthens (0.26% at a
5-day hold up to 8.88% at a 200-day hold, for a 5-day MD). This is distinct
from the repo's existing McGinley Dynamic strategy (2026-09-04-127, rejected
near-miss), which used a dual-fast/slow-MD-line CROSSOVER trend-following
rule with no mean-reversion price-vs-single-line trigger and no fixed-hold
exit -- this strategy instead trades PRICE crossing below a single MD line
(oversold dip-buy) with a source-disclosed fixed-day-count exit rather than
a signal-based exit.

Signal logic
------------
- McGinley Dynamic (single line): MD[0] = close[0]; for t>0,
  MD[t] = MD[t-1] + (close[t] - MD[t-1]) / (md_period * (close[t]/MD[t-1])**4)
- Entry (long): close crosses from >= MD to < MD (price dips below the MD
  line -- the source's "Strategy 3" oversold trigger).
- Exit: fixed `hold_days` after entry (source's own exit rule -- no
  signal-based exit at all, a genuine fixed-holding-period design, distinct
  from every other time-stop-as-backstop strategy in this repo where the
  time-stop is a safety net alongside a primary signal exit).
- Flat otherwise. Long-only, no re-entry while already in a position.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _mcginley_dynamic(close: pd.Series, md_period: int) -> pd.Series:
    md = pd.Series(index=close.index, dtype=float)
    md.iloc[0] = close.iloc[0]
    for t in range(1, len(close)):
        prev = md.iloc[t - 1]
        c = close.iloc[t]
        if prev == 0 or pd.isna(prev):
            md.iloc[t] = c
            continue
        ratio = c / prev
        denom = md_period * (ratio ** 4)
        if denom == 0 or pd.isna(denom):
            md.iloc[t] = prev
        else:
            md.iloc[t] = prev + (c - prev) / denom
    return md


def generate_signals(
    price_df: pd.DataFrame,
    md_period: int = 10,
    hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    md = _mcginley_dynamic(close, md_period)
    below = close < md
    crossunder = below & (~below.shift(1).fillna(False))

    position = pd.Series(0, index=df.index, dtype=int)

    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if held >= hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if bool(crossunder.iloc[i]):
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

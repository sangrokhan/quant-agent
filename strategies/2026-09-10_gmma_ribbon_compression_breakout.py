"""Strategy: Guppy Multiple Moving Average (GMMA) ribbon crossover, with a
compression/expansion volatility gate.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per StockCharts ChartSchool's GMMA guide
(https://chartschool.stockcharts.com/.../guppy-multiple-moving-average-an-ma-ribbon-designed-to-tip-the-markets-hand):
the GMMA is a 12-EMA ribbon split into a short-term group (3,5,8,10,12,15)
as a proxy for short-term traders and a long-term group (30,35,40,45,50,60)
as a proxy for long-term investors. Source's disclosed rule: a bullish
signal occurs when the short-term ribbon crosses above the long-term
ribbon, and the more "spread out" (separated) the ribbons are after the
cross, the stronger the trend; ribbon compression (convergence) signals low
volatility and a pending breakout. This strategy operationalizes the cross
using the AVERAGE of each ribbon (mean of the 6 EMAs in each group, a
standard simplification for the ribbon-vs-ribbon cross since comparing 12
individual lines pairwise is not a single tradeable signal), with an
optional "compression-then-expansion" refinement: only take the crossover
if the ribbons were compressed (narrow average gap) in the recent lookback,
per the source's framing that compression often precedes the more
significant breakouts. First GMMA strategy in this repo (0 prior entries)
-- distinct from other moving-average-crossover/ribbon strategies (single
fast/slow EMA or SMA pairs, 3-line Alligator SMMA) via its 12-line two-group
average-ribbon structure and the compression-precedes-breakout filter.

Signal logic
------------
- short_ribbon_avg = mean of EMA(3), EMA(5), EMA(8), EMA(10), EMA(12), EMA(15)
- long_ribbon_avg = mean of EMA(30), EMA(35), EMA(40), EMA(45), EMA(50), EMA(60)
- ribbon_gap_pct = (short_ribbon_avg - long_ribbon_avg) / long_ribbon_avg
- Entry (long): short_ribbon_avg crosses above long_ribbon_avg AND the
  ribbons were compressed (|ribbon_gap_pct| below compression_threshold at
  any point) within the trailing compression_lookback days before the
  cross -- per source's "compression precedes breakout" framing.
- Exit: short_ribbon_avg crosses back below long_ribbon_avg, or a
  max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd

SHORT_PERIODS = [3, 5, 8, 10, 12, 15]
LONG_PERIODS = [30, 35, 40, 45, 50, 60]


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ribbon_avg(close: pd.Series, periods: list) -> pd.Series:
    emas = [close.ewm(span=p, adjust=False).mean() for p in periods]
    return sum(emas) / len(emas)


def generate_signals(
    price_df: pd.DataFrame,
    compression_threshold: float = 0.02,
    compression_lookback: int = 20,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    short_avg = _ribbon_avg(close, SHORT_PERIODS)
    long_avg = _ribbon_avg(close, LONG_PERIODS)
    ribbon_gap_pct = (short_avg - long_avg) / long_avg

    bullish_cross = (short_avg > long_avg) & (short_avg.shift(1) <= long_avg.shift(1))
    bearish_cross = (short_avg < long_avg) & (short_avg.shift(1) >= long_avg.shift(1))

    was_compressed = (
        ribbon_gap_pct.abs().rolling(compression_lookback).min() <= compression_threshold
    )

    valid = long_avg.notna() & short_avg.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = None

    for i in range(len(df.index)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue

        if in_position:
            held_days = i - entry_idx
            if bearish_cross.iloc[i] or held_days >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bullish_cross.iloc[i] and was_compressed.iloc[i]:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    compression_threshold: float = 0.02,
    compression_lookback: int = 20,
    max_hold_days: int = 30,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        compression_threshold=compression_threshold,
        compression_lookback=compression_lookback,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_ret
    strat_returns.name = "strategy_returns"
    return strat_returns

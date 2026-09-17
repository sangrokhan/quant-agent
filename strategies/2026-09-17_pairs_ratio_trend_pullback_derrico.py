"""Strategy: Pairs Trend & Pullback on price-ratio dual-MA (Domenico D'Errico,
TASC Dec 2016 "Pair Trading With A Twist").

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-138):
Per Domenico D'Errico's "Pair Trading With A Twist" (TASC Dec 2016;
TradeStation EasyLanguage "PairsStrategy" code disclosed at
https://traders.com/Documentation/FEEDbk_docs/2016/12/TradersTips.html),
a price-RATIO between two related securities (source: e.g. XLE/SPY) is
smoothed by a fast (12) and slow (40) moving average. The source's own
"Trend & Pullback" mode (TrendFollow_123=3): when the fast average is above
the slow average (established uptrend in the ratio) AND the ratio itself
pulls back to cross UNDER the fast average, buy the strength leg (long the
numerator symbol) on the pullback -- a trend-continuation entry timed on a
minor pullback, not a fresh breakout. This repo trades a single primary
symbol long-only (no short leg), so only the source's "buy the numerator"
branch is implemented; the source's mirror short-the-numerator branch
becomes this strategy's flat/exit trigger instead.

This is distinct from the existing SPY/QQQ regression-hedge z-score pairs
strategy (2026-09-04-098) since that trades MEAN REVERSION of a
regression-hedged spread's z-score, while this trades TREND CONTINUATION
via a pullback on a raw price-ratio's own dual-MA crossover state -- an
entirely different pairs-trading mechanic per the source's own taxonomy.

Signal logic
------------
- ratio[t] = primary_close[t] / hedge_close[t] (hedge_symbol fetched
  internally via data/loaders.py, mirroring 2026-09-04-098's pattern).
- fast_avg = SMA(ratio, fast_length); slow_avg = SMA(ratio, slow_length).
- uptrend = fast_avg > slow_avg (source's own trend-state condition).
- pullback_entry = ratio crosses under fast_avg while uptrend is active
  (source's own "FastAvg > SlowAvg and SprdRatioC crosses under FastAvg").
- Entry (long primary symbol): pullback_entry.
- Exit: ratio crosses back over fast_avg (source's own mirror condition,
  translated from "close short" to "close long"), OR the trend state flips
  (fast_avg <= slow_avg), OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity, load_crypto  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_hedge_close(price_df_index, hedge_symbol: str) -> pd.Series:
    start, end = price_df_index.min(), price_df_index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None)
    loader = load_crypto if "/" in hedge_symbol else load_equity
    hedge_df = _prep(loader(hedge_symbol, start, end))
    return hedge_df["close"].reindex(price_df_index, method="ffill")


def generate_signals(
    price_df: pd.DataFrame,
    hedge_symbol: str = "SPY",
    fast_length: int = 12,
    slow_length: int = 40,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    hedge_close = _load_hedge_close(df.index, hedge_symbol)

    ratio = close / hedge_close
    fast_avg = ratio.rolling(fast_length).mean()
    slow_avg = ratio.rolling(slow_length).mean()

    uptrend = fast_avg > slow_avg
    pullback_entry = (ratio < fast_avg) & (ratio.shift(1) >= fast_avg.shift(1)) & uptrend
    exit_reclaim = (ratio > fast_avg) & (ratio.shift(1) <= fast_avg.shift(1))
    exit_trend_flip = ~uptrend

    entry = pullback_entry.fillna(False)
    exit_signal = exit_reclaim.fillna(False) | exit_trend_flip.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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

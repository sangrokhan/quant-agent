"""Strategy: Kaufman's "Stress" Pairs-Logic Mean Reversion vs SPY ("Timing
The Market With Pairs Logic", Perry J. Kaufman, TASC March 2014), long-only
adaptation. Read this iteration via browser_exec at
https://traders.com/documentation/feedbk_docs/2014/03/traderstips.html
(EasyLanguage/thinkScript code disclosed directly in the article's
TradeStation and thinkorswim Traders' Tips code sections).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-117):
Kaufman's "Stress" indicator is a stochastic-of-a-stochastic-DIFFERENCE: take
a rolling %-stochastic of the target symbol's close (position within its own
N-bar high/low range) and of a reference INDEX (here fixed to SPY, matching
the source's own examples), subtract the two stochastics, then take a
rolling %-stochastic OF THAT DIFFERENCE itself (Stress, bounded 0-100). Low
Stress (<=10, per the thinkorswim strategy's own entryLevel default) means
the target has been persistently UNDERPERFORMING the index on a
stochastic-relative basis -- a pairs-style relative-value dip. The source's
disclosed entry additionally requires an "isReady" gate: Stress must have
first risen ABOVE 50 (a "reset" showing the pair wasn't already stressed) at
some point since the last crisis-stop exit before a new sub-10 entry is
armed -- preventing repeated re-entries into a persistently-depressed pair.
Exit when Stress recovers to exitLevel (50, per source default) OR a
crisis stop (target price down >=10% from entry). This is distinct from the
repo's existing single-asset stochastic/relative-strength entries (e.g.
relative_strength_comparative.py, rsi2_meanrev) because it applies a
DOUBLE stochastic transform to a cross-asset difference series, not a
plain single-asset oscillator.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
        NOTE: this strategy internally fetches the SPY index series via
        data/loaders.py's load_equity (matching the article's own fixed
        SPY reference) rather than taking it as a second price_df arg, to
        preserve the single-price_df generate_signals/generate_returns
        contract required by validation/grid_test.py.
"""

from __future__ import annotations

import sys
import os
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _stochastic(close: pd.Series, high: pd.Series, low: pd.Series, period: int) -> pd.Series:
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    rng = hh - ll
    stoch = (close - ll) / rng.replace(0, pd.NA)
    return stoch.fillna(0.5)


def _stress_indicator(df: pd.DataFrame, index_df: pd.DataFrame, period: int) -> pd.Series:
    stoch1 = _stochastic(df["close"], df["high"], df["low"], period)
    stoch2 = _stochastic(index_df["close"], index_df["high"], index_df["low"], period)
    stoch2 = stoch2.reindex(stoch1.index).ffill()

    diff = stoch1 - stoch2
    hh_diff = diff.rolling(period).max()
    ll_diff = diff.rolling(period).min()
    rng_diff = hh_diff - ll_diff
    stress = 100.0 * (diff - ll_diff) / rng_diff.replace(0, pd.NA)
    return stress.fillna(50.0)


def _load_index(df_index_range: pd.DatetimeIndex, index_symbol: str = "SPY") -> pd.DataFrame:
    from loaders import load_equity

    start = df_index_range.min().to_pydatetime()
    end = df_index_range.max().to_pydatetime()
    idx_df = load_equity(index_symbol, start, end, interval="1d")
    if "timestamp" in idx_df.columns:
        idx_df = idx_df.set_index("timestamp")
    return idx_df.sort_index()


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 50,
    entry_level: float = 10.0,
    exit_level: float = 50.0,
    crisis_stop_pct: float = 0.10,
    index_symbol: str = "SPY",
) -> pd.Series:
    """Return a {0,1} long/flat position series per Kaufman's Stress
    pairs-logic rule (long-only adaptation, fixed SPY reference index)."""
    df = _prep(price_df)
    index_df = _load_index(df.index, index_symbol)

    stress = _stress_indicator(df, index_df, period)
    close = df["close"]

    ready_armed = stress > 50.0  # "reset" condition per thinkorswim isReady gate

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_price = None
    is_ready = False
    for i in range(len(df)):
        if bool(ready_armed.iloc[i]):
            is_ready = True

        if in_position:
            crisis_stop_hit = (
                entry_price is not None and (close.iloc[i] / entry_price - 1.0) < -crisis_stop_pct
            )
            if bool(stress.iloc[i] >= exit_level) or crisis_stop_hit:
                in_position = False
                entry_price = None
                if crisis_stop_hit:
                    is_ready = False  # per source: crisis stop resets the ready gate
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if is_ready and bool(stress.iloc[i] <= entry_level):
                in_position = True
                entry_price = float(close.iloc[i])
                is_ready = False
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

"""Strategy: Nick Radge Weekend Trend Trader with SPY as FIXED external
market-regime reference (rescue attempt for 2026-09-18-072's near-miss).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Direct fix attempt for 2026-09-18-072 (Weekend Trend Trader, self-referential
regime filter -- SPY Sharpe 0.696 near-miss, all other validators passed,
only 7 trades over 8.7 years). -072's own notes flagged the self-referential
regime substitution (using the traded asset's OWN 10-week SMA instead of a
genuine external index) as the most likely source of degraded edge versus
the source's design. This iteration uses SPY itself as a FIXED external
market-regime reference for gating QQQ's (and other non-SPY assets')
entries -- QQQ's own new-high/ROC triggers stay identical, but the
"is the market in an uptrend" regime check now looks at SPY's 10-week SMA
(a genuine, fixed, broad-market proxy) rather than QQQ's own weekly chart.
For SPY itself (traded as the primary asset), the regime filter necessarily
remains self-referential (SPY IS the market proxy in that case) -- this
rescue specifically targets QQQ and other non-index-proxy assets.

Source: https://usethinkscript.com/threads/weekend-trend-trader-by-nick-radge-strategy-for-thinkorswim.669/
(same as -072; this fix is this repo's own extension using SPY as the
"market" argument the source's own ThinkorSwim code already parameterizes
via `input market = {default SPX, NDX, RUT, DJX}` -- i.e. this directly
implements the source's OWN intended design, which -072 had approximated
away due to lacking a literal index feed).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import sys
import os
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

_regime_cache: dict = {}


def _load_regime_weekly_close(index: pd.DatetimeIndex, regime_symbol: str) -> pd.Series:
    from loaders import load_equity

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    cache_key = (regime_symbol, start, end)
    if cache_key in _regime_cache:
        return _regime_cache[cache_key]

    df = load_equity(regime_symbol, start, end)
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    weekly_close = df["close"].resample("W-FRI").last().dropna()
    _regime_cache[cache_key] = weekly_close
    return weekly_close


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _weekly_signals(
    df: pd.DataFrame,
    regime_window: int,
    high_window: int,
    roc_window: int,
    roc_threshold: float,
    init_trail_pct: float,
    downtrend_trail_pct: float,
    regime_weekly_close: pd.Series,
) -> pd.Series:
    """Compute the weekly {0,1} position series, forward-filled to daily."""
    weekly_close = df["close"].resample("W-FRI").last().dropna()

    regime_sma_full = regime_weekly_close.rolling(regime_window).mean()
    regime_aligned = regime_weekly_close.reindex(weekly_close.index, method="ffill")
    regime_sma = regime_sma_full.reindex(weekly_close.index, method="ffill")
    regime_up = regime_aligned > regime_sma

    rolling_high_full = weekly_close.rolling(high_window).max()
    new_high = weekly_close >= rolling_high_full

    weekly_roc = weekly_close.pct_change(roc_window)

    entry_signal = new_high & regime_up & (weekly_roc > roc_threshold)

    recent_high_lag = weekly_close.rolling(max(1, high_window - 1)).max()
    loss_pct = pd.Series(
        [init_trail_pct if up else downtrend_trail_pct for up in regime_up],
        index=weekly_close.index,
    )
    raw_stop = recent_high_lag * (1 - loss_pct)

    position = pd.Series(0, index=weekly_close.index, dtype=int)
    in_position = False
    ratcheted_stop = None

    for i in range(len(weekly_close)):
        price = weekly_close.iloc[i]
        if not in_position:
            if bool(entry_signal.iloc[i]) if pd.notna(entry_signal.iloc[i]) else False:
                in_position = True
                ratcheted_stop = raw_stop.iloc[i] if pd.notna(raw_stop.iloc[i]) else None
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
        else:
            candidate_stop = raw_stop.iloc[i]
            if pd.notna(candidate_stop):
                ratcheted_stop = candidate_stop if ratcheted_stop is None else max(ratcheted_stop, candidate_stop)
            if ratcheted_stop is not None and price <= ratcheted_stop:
                in_position = False
                ratcheted_stop = None
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1

    return position


def generate_signals(
    price_df: pd.DataFrame,
    regime_window: int = 10,
    high_window: int = 20,
    roc_window: int = 20,
    roc_threshold: float = 0.30,
    init_trail_pct: float = 0.40,
    downtrend_trail_pct: float = 0.10,
    regime_symbol: str = "SPY",
) -> pd.Series:
    """Return a {0,1} long/flat DAILY position series (forward-filled from
    the weekly signal, applied on the FOLLOWING trading day per the
    source's Friday-close-decide / Monday-open-execute cadence)."""
    df = _prep(price_df)
    regime_weekly_close = _load_regime_weekly_close(df.index, regime_symbol)
    weekly_position = _weekly_signals(
        df, regime_window, high_window, roc_window, roc_threshold,
        init_trail_pct, downtrend_trail_pct, regime_weekly_close,
    )
    # Shift weekly decision by one week (decided Friday, executed next week)
    # then forward-fill onto the daily index.
    weekly_position_shifted = weekly_position.shift(1).fillna(0).astype(int)
    daily_position = weekly_position_shifted.reindex(df.index, method="ffill").fillna(0).astype(int)
    return daily_position


def generate_returns(
    price_df: pd.DataFrame,
    regime_window: int = 10,
    high_window: int = 20,
    roc_window: int = 20,
    roc_threshold: float = 0.30,
    init_trail_pct: float = 0.40,
    downtrend_trail_pct: float = 0.10,
    regime_symbol: str = "SPY",
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        regime_window=regime_window,
        high_window=high_window,
        roc_window=roc_window,
        roc_threshold=roc_threshold,
        init_trail_pct=init_trail_pct,
        downtrend_trail_pct=downtrend_trail_pct,
        regime_symbol=regime_symbol,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

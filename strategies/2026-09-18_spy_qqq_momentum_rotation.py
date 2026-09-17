"""Strategy: SPY/QQQ trailing-momentum monthly rotation (long the stronger
of the two ETFs based on trailing N-day total return).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-024):
Per https://github.com/ManusMcMeen/spy-qqq-rotation-strategy's disclosed
README (visited this iteration via browser_exec after web_extract errored
with "DuckDuckGo (ddgs) is a search-only backend and cannot extract URL
content"): a systematic strategy that rotates between SPY and QQQ based on
trailing 3-month (63 trading day) total return -- at each month-end, invest
100% in whichever of SPY/QQQ had the higher trailing lookback return for the
following month, rebalanced monthly. The source's own reported backtest
(2023-01-01 to 2025-08-07, a short ~2.6yr sample) claimed CAGR 17.39%,
Sharpe 1.29 -- this repo tests the identical mechanical rule independently
over this repo's full available QQQ/SPY history rather than assuming the
short-sample result transfers.

This is a genuine relative-strength ROTATION construction (always fully
invested in one of two assets, never flat) -- distinct from every other
single-asset trend/momentum/mean-reversion strategy in this repo, and from
the existing GLD/SLV, JPM/BAC, GDX/RING, ETH/BTC single-leg-approximation
pairs-trade strategies (which all trade ONE leg long/flat based on a ratio
signal) since this construction is ALWAYS long one of the two ETFs, never
flat, and directly rotates capital between them rather than gating a single
asset's exposure.

Because this repo's `run_strategy_grid`/`load_equity`/`load_crypto` loader
plumbing is single-symbol per grid cell, this strategy is implemented as a
single `generate_returns(spy_df, qqq_df, **params)`-style function operating
on BOTH price series directly (both fetched via data/loaders.py::load_equity
by the calling script) -- NOT the standard single-price_df contract, since a
genuine two-asset rotation strategy cannot express its returns as a
function of only one asset's OHLCV. generate_signals/generate_returns are
still exposed with the standard kwarg-based param contract but take a
second required positional/keyword argument `other_price_df` for the second
leg. See validation script this iteration for the custom grid-test harness
adaptation required (this deviates from the strict Step 6 grid_test.py
one-price_df convention, noted explicitly in the backtest report).

Interface:
    generate_signals(price_df, other_price_df, **params) -> pd.Series
        (1 = long price_df's asset, 0 = long other_price_df's asset -- always
        one or the other, never flat)
    generate_returns(price_df, other_price_df, **params) -> pd.Series
        Daily strategy returns of the FIRST asset (price_df) when signal==1,
        the SECOND asset (other_price_df) when signal==0.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    other_price_df: pd.DataFrame,
    lookback_days: int = 63,
    rebalance_freq_days: int = 21,  # ~1 month of trading days
) -> pd.Series:
    """Return a {0,1} series: 1 = hold price_df's asset, 0 = hold
    other_price_df's asset (always one or the other -- rotation, not a
    long/flat gate)."""
    df_a = _prep(price_df)
    df_b = _prep(other_price_df)

    close_a = df_a["close"]
    close_b = df_b["close"].reindex(close_a.index).ffill()

    ret_a = close_a.pct_change(lookback_days)
    ret_b = close_b.pct_change(lookback_days)

    # Determine rebalance dates: every rebalance_freq_days bars.
    n = len(close_a)
    rebalance_idx = set(range(0, n, rebalance_freq_days))

    position = pd.Series(0, index=close_a.index, dtype=int)
    current_hold_a = True  # default state before first valid comparison
    for i in range(n):
        if i in rebalance_idx and not (pd.isna(ret_a.iloc[i]) or pd.isna(ret_b.iloc[i])):
            current_hold_a = bool(ret_a.iloc[i] >= ret_b.iloc[i])
        position.iloc[i] = 1 if current_hold_a else 0
    return position


def generate_returns(price_df: pd.DataFrame, other_price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Daily returns: asset A's return when position==1, asset B's when 0."""
    df_a = _prep(price_df)
    df_b = _prep(other_price_df)
    close_a = df_a["close"]
    close_b = df_b["close"].reindex(close_a.index).ffill()

    position = generate_signals(price_df, other_price_df, **kwargs)
    ret_a = close_a.pct_change().fillna(0.0)
    ret_b = close_b.pct_change().fillna(0.0)
    # Shift by 1 day to avoid look-ahead (yesterday's rotation decision
    # determines today's exposure).
    pos_shifted = position.shift(1).fillna(1).astype(int)
    strategy_ret = pos_shifted * ret_a + (1 - pos_shifted) * ret_b
    return strategy_ret

"""Strategy: TQQQ/TMF Risk-Mitigation Portfolio with Crash Filter.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per QuantifiedStrategies.com's "Triple Leveraged ETF Trading Strategy (44%
Annual Returns)" (https://www.quantifiedstrategies.com/triple-leveraged-etf-trading-strategy/,
visited this iteration via browser_exec fallback), based on Lewis Glenn's
2020 paper "Long-Term Investing in Triple Leveraged Exchange Traded Funds"
(updated by SetupAlpha through Oct 2025): hold an equal-dollar 50/50
portfolio of TQQQ (3x leveraged Nasdaq-100) and TMF (3x leveraged 20+yr
Treasury), rebalanced bimonthly (every 2 months), exploiting TQQQ/TMF's
generally negative correlation to reduce TQQQ-alone's severe drawdowns
while retaining much of its upside. Crash filter: if TQQQ drops >=20% in a
single day, exit both TQQQ and TMF entirely and move 100% into IEF (7-10yr
Treasury, unleveraged) until TQQQ's price recovers back above its
pre-crash level, then resume the 50/50 TQQQ/TMF split.

Source's own disclosed full-history results: CAGR 44.9%, max EOM drawdown
24.5% (vs TQQQ-alone's 49.1%), though 2022 (stocks AND bonds falling
together) was a hard period with "no place to hide" per the source's own
admission -- a candid caveat going into this test.

Adapted to this repo's single-asset generate_signals/generate_returns
interface: the "primary asset" passed in as price_df determines which
symbol drives the crash-filter trigger and return series (TQQQ is the
intended primary; QQQ/SPY/crypto are tested as falsification/generalization
checks using the SAME mechanism applied to their own price series, i.e.
"would a leveraged-pair mitigation strategy on this asset combined with
TMF/IEF as the defensive leg work generally, not just for TQQQ
specifically"). generate_returns internally loads TMF and IEF via
data/loaders.py (the "internal basket load" pattern already used by this
repo's other multi-asset strategies, e.g. GEM dual momentum, GTAA rotation).

First leveraged-ETF-pair strategy in this repo -- distinct from every
single-asset trend/regime-gate strategy already tested, since this is a
genuine two-asset RISK-PARITY-STYLE portfolio with a discrete crash-filter
state machine, not a simple long/flat gate on one asset.

Interface contract for validators (see validation/validators.py) /
grid_test.py (see validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (weight in [0,1] on
        the primary asset -- NOT a strict {0,1}, since this is a 50%-
        weighted portfolio leg most of the time)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

_asset_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_defensive_legs(index: pd.DatetimeIndex, defensive_symbol: str, cash_symbol: str):
    """Load the defensive leg (default TMF) and the crash-filter cash-parking
    leg (default IEF) closes, reindexed/ffilled to the primary asset's index."""
    cache_key = (defensive_symbol, cash_symbol)
    if cache_key in _asset_cache:
        defensive_close, cash_close = _asset_cache[cache_key]
    else:
        from loaders import load_equity

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        defensive_close = _prep(load_equity(defensive_symbol, start, end))["close"]
        cash_close = _prep(load_equity(cash_symbol, start, end))["close"]
        _asset_cache[cache_key] = (defensive_close, cash_close)

    defensive_aligned = defensive_close.reindex(index, method="ffill")
    cash_aligned = cash_close.reindex(index, method="ffill")
    return defensive_aligned, cash_aligned


def generate_signals(
    price_df: pd.DataFrame,
    crash_threshold: float = -0.20,
    rebalance_days: int = 42,
    defensive_symbol: str = "TMF",
    cash_symbol: str = "IEF",
) -> pd.Series:
    """Return the PRIMARY asset's weight (0.0 to 0.5) at each bar:
    0.5 = normal 50/50 TQQQ/TMF regime, 0.0 = crash-filter regime (100% in
    the cash_symbol leg, 0% primary AND 0% defensive)."""
    df = _prep(price_df)
    close = df["close"]

    daily_ret = close.pct_change()
    defensive_close, cash_close = _load_defensive_legs(df.index, defensive_symbol, cash_symbol)

    n = len(close)
    weight_primary = [0.0] * n
    crash_active = False
    pre_crash_price = None
    close_arr = close.to_numpy()
    ret_arr = daily_ret.to_numpy()

    for i in range(n):
        if not crash_active:
            if ret_arr[i] is not None and ret_arr[i] <= crash_threshold:
                crash_active = True
                pre_crash_price = close_arr[i - 1] if i > 0 else close_arr[i]
                weight_primary[i] = 0.0
            else:
                weight_primary[i] = 0.5
        else:
            if close_arr[i] > pre_crash_price:
                crash_active = False
                weight_primary[i] = 0.5
            else:
                weight_primary[i] = 0.0

    return pd.Series(weight_primary, index=df.index, dtype=float).rename("position")


def generate_returns(
    price_df: pd.DataFrame,
    crash_threshold: float = -0.20,
    rebalance_days: int = 42,
    defensive_symbol: str = "TMF",
    cash_symbol: str = "IEF",
) -> pd.Series:
    """Daily returns of the two-leg (primary + defensive, or cash during a
    crash) portfolio, rebalanced every rebalance_days trading days back to
    50/50 (or reset to 100% cash_symbol upon a crash-filter trigger)."""
    df = _prep(price_df)
    close = df["close"]
    primary_weight_target = generate_signals(
        df,
        crash_threshold=crash_threshold,
        rebalance_days=rebalance_days,
        defensive_symbol=defensive_symbol,
        cash_symbol=cash_symbol,
    )
    defensive_close, cash_close = _load_defensive_legs(df.index, defensive_symbol, cash_symbol)

    primary_ret = close.pct_change().fillna(0.0)
    defensive_ret = defensive_close.pct_change().fillna(0.0)
    cash_ret = cash_close.pct_change().fillna(0.0)

    n = len(close)
    strat_ret = [0.0] * n
    # Track running weights, only rebalancing back to target every
    # rebalance_days bars (buy-and-hold drift in between) OR immediately on
    # a crash-filter state transition (handled by primary_weight_target
    # itself flipping to/from 0).
    cur_primary_w = primary_weight_target.iloc[0] if n > 0 else 0.0
    cur_defensive_w = cur_primary_w  # defensive leg mirrors primary's non-crash weight
    days_since_rebalance = 0

    target_arr = primary_weight_target.to_numpy()
    p_ret_arr = primary_ret.to_numpy()
    d_ret_arr = defensive_ret.to_numpy()
    c_ret_arr = cash_ret.to_numpy()

    for i in range(n):
        target_w = target_arr[i]
        in_crash = target_w == 0.0
        if in_crash:
            cur_primary_w = 0.0
            cur_defensive_w = 0.0
            cash_w = 1.0
            days_since_rebalance = 0
        else:
            cash_w = 0.0
            if i == 0 or target_arr[i - 1] == 0.0 or days_since_rebalance >= rebalance_days:
                # Reset to 50/50 upon exiting crash-filter or periodic rebalance.
                cur_primary_w = 0.5
                cur_defensive_w = 0.5
                days_since_rebalance = 0
            days_since_rebalance += 1

        bar_ret = cur_primary_w * p_ret_arr[i] + cur_defensive_w * d_ret_arr[i] + cash_w * c_ret_arr[i]
        strat_ret[i] = bar_ret

        # Let weights drift with relative performance until next rebalance
        # (standard buy-and-hold-between-rebalances mechanic).
        if not in_crash:
            grow_p = cur_primary_w * (1.0 + p_ret_arr[i])
            grow_d = cur_defensive_w * (1.0 + d_ret_arr[i])
            total = grow_p + grow_d
            if total > 0:
                cur_primary_w, cur_defensive_w = grow_p, grow_d

    return pd.Series(strat_ret, index=df.index, dtype=float).rename("returns")

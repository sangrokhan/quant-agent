"""Strategy: BTC/Gold ratio z-score mean reversion (single-leg long approximation).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-082):
Per https://blofin.com/en/academy/education/gold/gold-bitcoin-correlation-pairs-trade
(source's own worked example): the BTC/gold ratio can be z-scored against
its rolling mean/std; when the ratio sits far below its mean (bitcoin looks
cheap vs gold, z <= -entry_z), a mean-reversion pairs trade goes long BTC
and short gold, betting the gap narrows. The source itself is explicit that
this only works if the pair is truly cointegrated (not just correlated) and
warns the gold-bitcoin ratio has historically TRENDED rather than reverted
-- we test the source's own disclosed rule on this repo's data/validator
stack rather than trusting that verdict a priori, consistent with the
already-tested ETH/BTC spread precedent (2026-09-04-083, decisively broken).

This repo has no short-selling infrastructure, so (matching the pattern
established by strategies/2026-09-04_eth_btc_spread_zscore_pairs.py) we
approximate the "long the cheap leg" side only: long BTC/USDT when the
BTC/gold ratio z-score is unusually low, flat otherwise. This is NOT
market-neutral (does not short gold), a documented simplification.

Signal logic
------------
- ratio = close_btc / close_gold (BTC/USDT vs GLD, aligned by date)
- rolling mean/std of log(ratio) over `window` days -> z-score
- Entry (long BTC leg): z crosses below -entry_z (ratio unusually low,
  BTC cheap vs gold)
- Exit: z reverts to >= exit_z, OR |z| grows beyond stop_z (divergence
  continues against us), OR max_hold_days elapses.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
        price_df here is expected to be the BTC/USDT OHLCV frame; the gold
        leg (GLD) is fetched internally via data/loaders.py.
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_gold_series(index: pd.Index, start=None, end=None) -> pd.Series:
    """Fetch GLD close series aligned to the given index, via data/loaders.py."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    if start is None:
        start = index.min()
    if end is None:
        end = index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None) if hasattr(start, "tz_localize") else start.replace(tzinfo=None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None) if hasattr(end, "tz_localize") else end.replace(tzinfo=None)
    gold_df = load_equity("GLD", start=start, end=end)
    gold_df = _prep(gold_df)
    gold_close = gold_df["close"]
    # Align by calendar date: crypto index may be hourly/daily and include
    # weekends where GLD (equity, weekdays only) has no bar -- build a
    # date->price map and forward-fill across the crypto index's own dates.
    gold_by_date = gold_close.copy()
    gold_by_date.index = pd.to_datetime(gold_by_date.index).normalize()
    gold_by_date = gold_by_date[~gold_by_date.index.duplicated(keep="last")]

    target_dates = pd.to_datetime(index).normalize()
    full_date_range = pd.date_range(gold_by_date.index.min(), target_dates.max(), freq="D")
    gold_daily = gold_by_date.reindex(full_date_range).ffill()

    aligned = pd.Series(gold_daily.reindex(target_dates).values, index=index)
    return aligned.ffill()


def _compute_z(price_df: pd.DataFrame, window: int) -> pd.Series:
    df = _prep(price_df)
    close_btc = df["close"]
    close_gold = _get_gold_series(df.index)
    ratio = close_btc / close_gold
    log_ratio = np.log(ratio)
    rolling_mean = log_ratio.rolling(window).mean()
    rolling_std = log_ratio.rolling(window).std()
    z = (log_ratio - rolling_mean) / rolling_std
    return z


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 60,
    entry_z: float = 2.0,
    exit_z: float = 0.0,
    stop_z: float = 3.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series (long-BTC-leg approximation)."""
    df = _prep(price_df)
    z = _compute_z(df, window)
    z_prev = z.shift(1)
    entry_trigger = (z < -entry_z) & (z_prev >= -entry_z)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        zi = z.iloc[i]
        if in_pos:
            hold_count += 1
            reverted = (zi >= exit_z) if pd.notna(zi) else False
            stopped = (abs(zi) >= stop_z) if pd.notna(zi) else False
            if reverted or stopped or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            trig = entry_trigger.iloc[i]
            if bool(trig) if pd.notna(trig) else False:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    window: int = 60,
    entry_z: float = 2.0,
    exit_z: float = 0.0,
    stop_z: float = 3.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (long-only BTC leg, no shorting gold)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, window=window, entry_z=entry_z, exit_z=exit_z, stop_z=stop_z, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

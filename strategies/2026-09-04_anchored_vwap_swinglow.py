"""Strategy: Rolling-swing-low Anchored VWAP crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-138):
Per trendspider.com's Anchored VWAP (AVWAP) explainer, anchoring the
cumulative volume-weighted average price to a significant reference point
(e.g. a swing low, trend-reversal point) rather than session start gives
a level that reflects the "average cost basis" of everyone who has traded
since that meaningful point -- price staying above it signals sustained
buying control since the anchor, price crossing below signals a shift.
The source describes this as a discretionary support/resistance tool
without giving one fixed numeric rule, so this repo operationalizes it
mechanically: re-anchor whenever a new rolling `lookback`-day lowest-low
is made (that low becomes the new anchor bar), accumulate VWAP from that
anchor bar forward, and trade the crossover of close vs. that anchored
VWAP. This is the first VWAP-family (volume-weighted, not just price-
weighted) strategy tested in this repo.

Signal logic
------------
- anchor_idx[i] = the most recent bar index where low[i] was the lowest
  low over the trailing `lookback` bars (a fresh rolling swing low;
  re-anchors AVWAP whenever a new such low is confirmed).
- avwap[i] = cumulative sum(typical_price * volume) / cumulative
  sum(volume), accumulated from anchor_idx[i] through bar i.
- Entry (long): close crosses above avwap (fresh cross).
- Exit: close crosses below avwap, OR max_hold_days time-stop.
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _anchored_vwap(df: pd.DataFrame, lookback: int) -> pd.Series:
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    volume = df["volume"].to_numpy() if "volume" in df.columns else np.ones(len(df))
    typical = (high + low + close) / 3.0
    n = len(df)

    avwap = np.full(n, np.nan)
    anchor_idx = 0
    cum_pv = 0.0
    cum_v = 0.0

    for i in range(n):
        # Determine the rolling lowest-low anchor as of bar i (using data
        # up to and including bar i -- causal, no look-ahead).
        start = max(0, i - lookback + 1)
        window_low = low[start:i + 1]
        local_min_pos = start + int(np.argmin(window_low))

        if local_min_pos != anchor_idx:
            # Re-anchor: restart accumulation from the new anchor bar.
            anchor_idx = local_min_pos
            cum_pv = 0.0
            cum_v = 0.0
            for j in range(anchor_idx, i + 1):
                cum_pv += typical[j] * volume[j]
                cum_v += volume[j]
        else:
            cum_pv += typical[i] * volume[i]
            cum_v += volume[i]

        avwap[i] = cum_pv / cum_v if cum_v > 0 else np.nan

    return pd.Series(avwap, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 40,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    avwap = _anchored_vwap(df, lookback)
    close_prev = close.shift(1)
    avwap_prev = avwap.shift(1)

    entry_trigger = (close > avwap) & (close_prev <= avwap_prev)
    exit_trigger = (close < avwap) & (close_prev >= avwap_prev)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            et = bool(exit_trigger.iloc[i]) if pd.notna(exit_trigger.iloc[i]) else False
            if et or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entered = bool(entry_trigger.iloc[i]) if pd.notna(entry_trigger.iloc[i]) else False
            if entered:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    lookback: int = 40,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(df, lookback=lookback, max_hold_days=max_hold_days)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

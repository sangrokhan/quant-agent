"""Strategy: Donchian-channel price breakout, confirmed by a Volume Rate of
Change (VROC) participation threshold.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per UEEx's "Volume Rate of Change (VROC): How to Use It to Confirm Trades"
(https://blog.ueex.com/volume-rate-of-change-vroc/), VROC = [(current
volume - volume N periods ago) / volume N periods ago] * 100 measures
volume participation relative to a lookback. The source's own disclosed
rule: "a VROC reading above 200% is considered strong breakout
validation... a VROC spike below 100% during a price breakout warrants
skepticism... wait for VROC to exceed the 200% threshold before treating a
breakout as confirmed." This strategy operationalizes that directly: a
Donchian-channel breakout (close breaks above its own prior N-day rolling
high, the standard breakout entry construction already used elsewhere in
this repo, e.g. strategies/2026-09-04_donchian_turtle_breakout.py) is only
taken as a valid long entry if same-bar VROC exceeds `vroc_threshold`
(default 200, i.e. 200%) -- volume must have more than doubled relative to
`vroc_lookback` periods ago, confirming genuine breadth-of-participation
behind the breakout rather than a low-conviction move. This is the first
strategy in this repo pairing a price-based Donchian breakout entry filter
with a volume-rate-of-change (as opposed to dollar-flow/typical-price
volume, or a volume oscillator like Klinger/PVO/KVO already tested)
confirmation gate.

Signal logic
------------
- Donchian upper channel: rolling max of close over `channel_window` bars
  (excluding the current bar, i.e. shifted by 1, so "breaks above" means a
  genuine new high not already priced into the channel).
- VROC = 100 * (volume - volume.shift(vroc_lookback)) / volume.shift(vroc_lookback).
- Entry (long): close crosses above the prior `channel_window`-bar rolling
  high of close AND same-bar VROC >= vroc_threshold.
- Exit: close crosses below the rolling `channel_window`-bar low (Donchian
  lower-channel breakdown, standard exit for breakout systems), OR a
  max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators/grid_test:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    channel_window: int = 20,
    vroc_lookback: int = 14,
    vroc_threshold: float = 200.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    upper_channel = close.rolling(channel_window).max().shift(1)
    lower_channel = close.rolling(channel_window).min().shift(1)

    vol_ago = volume.shift(vroc_lookback)
    vroc = 100.0 * (volume - vol_ago) / vol_ago.replace(0, pd.NA)
    vroc = vroc.fillna(-999.0)  # treat undefined VROC as "not confirmed"

    breakout = close > upper_channel
    vroc_confirmed = vroc >= vroc_threshold
    entry = breakout & vroc_confirmed
    exit_breakdown = close < lower_channel

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    n = len(close)
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_breakdown.iloc[i]) or held >= max_hold_days:
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

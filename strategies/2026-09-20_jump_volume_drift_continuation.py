"""Strategy: Price/volume-only proxy for Post-Earnings-Announcement Drift
(PEAD) -- "jump + volume confirmation" continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Per quantmemo.com's "Post-Earnings Announcement Drift" strategy write-up
(https://quantmemo.com/strategies/earnings-drift-pead, read via browser_exec
after web_extract's DDG-only backend refused to fetch it), the underlying
mechanism of PEAD is: (1) a large, information-laden one-day price move
("announcement return") that (2) the market under-reacts to, so price keeps
"drifting" in the same direction for weeks afterward, and (3) the effect is
reinforced by attention/volume at the event (the source explicitly lists
"Volume and attention at announcement" as one of the four core signals, and
notes the drift is stronger when the announcement was "under-noticed").

This repo has no point-in-time earnings-calendar/analyst-consensus data
source (data/loaders.py only exposes plain OHLCV via yfinance/ccxt), so a
literal SUE-based PEAD strategy isn't implementable here. Instead this
strategy tests the OHLCV-only *proxy* the source itself flags as important
even without earnings dates: a statistically large one-day return (z-scored
against its own recent volatility, standing in for "a big informational
jump just happened") confirmed by an above-average volume day (standing in
for "the market noticed"), followed by a fixed holding period long
(drift-capture) exit. This is a genuinely new indicator-family/technique
combination in this repo (checked: no prior entry keyed on "jump
continuation", "large move drift", or "gap drift" combines a return
z-score AND a volume-confirmation gate with a fixed post-event hold).

Signal logic
------------
- Daily return; a rolling window's std of daily returns gives an
  "expected" move size.
- Entry trigger: today's return >= jump_std_mult * rolling std of returns
  (a large positive one-day jump) AND today's volume >= volume_mult * its
  own rolling average volume (attention/volume confirmation, per the
  source's 4th core signal).
- Enter long the next trading day (avoid look-ahead), hold for exactly
  hold_days trading days (drift-capture window), then flat.
- Long-only (proxy for the "buy the positive surprises" side of PEAD;
  the short side needs shortability infra out of scope here).
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
    jump_std_mult: float = 2.0,
    jump_lookback: int = 20,
    volume_mult: float = 1.5,
    volume_lookback: int = 20,
    hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    daily_ret = close.pct_change()
    rolling_std = daily_ret.rolling(jump_lookback).std()
    avg_volume = volume.rolling(volume_lookback).mean()

    jump_trigger = daily_ret >= (jump_std_mult * rolling_std)
    volume_trigger = volume >= (volume_mult * avg_volume)
    entry = (jump_trigger & volume_trigger).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= hold_days:
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

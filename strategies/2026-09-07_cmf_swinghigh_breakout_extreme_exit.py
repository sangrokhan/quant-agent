"""Strategy: Chaikin Money Flow (CMF) zero-cross + swing-high breakout
confirmation, with extreme-reading curl-back exit (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-016):
Per https://theindicatorlab.com/reviews/chaikin-money-flow-cmf/ (source's
own disclosed "strategy that worked best in my testing"):

    Long entry: Wait for CMF to cross above zero and price to close above a
    recent swing high. The combination filters out weak bounces.
    Exit: Take profit when CMF reaches extreme readings (+0.25) and starts
    to curl back, or trail your stop once CMF stays on your side of the
    zero line.
    Avoid trading when CMF is hovering in the -0.05 to +0.05 range (no edge).

This is distinct from the repo's existing CMF strategy
(2026-09-04_cmf_threshold_trend_filter.py, id 2026-09-04-043) which gates
entry with an SMA trend filter and exits on a plain cross-back-below-zero;
here the entry confirmation is a swing-high price breakout (not an SMA
regime filter) and the exit is an extreme-reading (+0.25) curl-back
(momentum exhaustion), falling back to a cross-below-zero safety exit if the
extreme is never reached.

CMF formula (standard, window periods):
    MFM (Money Flow Multiplier) = ((close - low) - (high - close)) / (high - low)
    MFV (Money Flow Volume) = MFM * volume
    CMF = sum(MFV, window) / sum(volume, window)

Signal logic
------------
- Entry (long): CMF crosses above zero on this bar (was <=0 last bar, >0
  this bar) AND CMF was NOT already above `noise_band` before crossing (i.e.
  a genuine cross, not just remaining in a noisy band) AND close breaks
  above the highest close of the prior `swing_lookback` bars (a recent swing
  high).
- Exit: EITHER (a) CMF reaches `extreme_threshold` (e.g. 0.25) and then
  curls back down (CMF this bar < CMF previous bar, having previously been
  >= extreme_threshold within the current trade), OR (b) CMF crosses back
  below zero (safety exit if the extreme is never reached), OR (c) a
  `max_hold_days` time-stop as an additional safety net (source doesn't
  specify one, but this repo consistently adds one to bound worst-case
  holding period for validator/backtest tractability).
- Avoid entries when CMF is within [-noise_band, +noise_band] at the moment
  of the would-be cross (source's "indecision zone" filter).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _cmf(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close, vol = df["high"], df["low"], df["close"], df["volume"]
    rng = (high - low).replace(0, np.nan)
    mfm = ((close - low) - (high - close)) / rng
    mfm = mfm.fillna(0.0)
    mfv = mfm * vol
    cmf = mfv.rolling(window).sum() / vol.rolling(window).sum().replace(0, np.nan)
    return cmf.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    cmf_window: int = 20,
    swing_lookback: int = 20,
    noise_band: float = 0.05,
    extreme_threshold: float = 0.25,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    cmf = _cmf(df, cmf_window)

    swing_high = close.shift(1).rolling(swing_lookback).max()

    cross_up = (cmf > 0) & (cmf.shift(1) <= 0) & (cmf.shift(1).abs() <= noise_band)
    breakout = close > swing_high
    entry_signal = cross_up & breakout

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    reached_extreme = False

    cmf_vals = cmf.values
    close_vals = close.values
    entry_sig_vals = entry_signal.values

    for i in range(n):
        if not in_pos:
            if entry_sig_vals[i]:
                in_pos = True
                entry_idx = i
                reached_extreme = False
            position.iloc[i] = 1 if in_pos else 0
            continue

        # already in position at start of this bar
        held = i - entry_idx
        if cmf_vals[i] >= extreme_threshold:
            reached_extreme = True

        exit_curl_back = reached_extreme and cmf_vals[i] < cmf_vals[i - 1]
        exit_zero_cross = cmf_vals[i] < 0 and cmf_vals[i - 1] >= 0
        exit_time_stop = held >= max_hold_days

        if exit_curl_back or exit_zero_cross or exit_time_stop:
            in_pos = False
            position.iloc[i] = 0
        else:
            position.iloc[i] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

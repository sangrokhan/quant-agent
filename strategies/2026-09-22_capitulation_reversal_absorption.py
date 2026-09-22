"""Strategy: Capitulation Reversal (RSI oversold + volume spike + close absorption).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-104):
Per ChartCrypto.app's "Capitulation Reversal" backtesting strategy page
(https://chartcrypto.app/backtesting/capitulation-reversal), a genuine
selling-climax reversal requires THREE simultaneous signatures on the same
bar, not just RSI-oversold-plus-volume:
  1. RSI(14) < 32 (stretched to the downside)
  2. volume >= 1.5x its own 20-bar average (forced-seller exhaustion)
  3. close in the UPPER HALF of the bar's own high-low range
     (close >= (high+low)/2) -- "someone absorbed the selling into the
     close", the actual reversal fingerprint absent from RSI-oversold-alone
     or RSI+volume-alone constructions.

Source's own stated rationale for condition 3 specifically: "A deeply
oversold bar on huge volume can still close on its lows -- sellers in total
control. A close above (H+L)/2 on capitulation volume means someone
absorbed the selling into the close... Without it, oversold alone catches
falling knives."

Exit: RSI normalizes above 50, OR price undercuts the prior 10-bar low
(thesis failure), backstopped by a max_hold_days time-stop.

Distinct from this repo's existing RSI+volume capitulation entry
(2026-09-05-083, decisively rejected: RSI(14)<30 + volume>=1.5x with NO
close-location filter, entering on the RSI-recovery bar rather than the
capitulation bar itself, exit RSI>60) -- this version adds the exact
close-in-upper-half absorption condition the source claims is the missing
"reversal fingerprint," enters directly on the capitulation bar (not the
later recovery), and uses a different asymmetric exit (RSI>50 OR
undercut-prior-low thesis-invalidation, not a fixed RSI>60 threshold).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _compute_rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    safe_loss = avg_loss.where(avg_loss != 0, 1e-12)
    rs = avg_gain / safe_loss
    rsi = 100 - 100 / (1 + rs)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    rsi_entry_threshold: float = 32.0,
    volume_ratio_threshold: float = 1.5,
    volume_window: int = 20,
    rsi_exit_threshold: float = 50.0,
    invalidation_lookback: int = 10,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    rsi = _compute_rsi(close, rsi_window)
    avg_volume = volume.rolling(volume_window).mean()
    vol_ratio = volume / avg_volume.where(avg_volume != 0, 1.0)
    midpoint = (high + low) / 2.0
    close_absorbed = close >= midpoint

    entry_trigger = (rsi < rsi_entry_threshold) & (vol_ratio >= volume_ratio_threshold) & close_absorbed

    prior_low = low.rolling(invalidation_lookback).min().shift(1)
    exit_rsi = rsi > rsi_exit_threshold
    exit_invalidation = close < prior_low

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_rsi.iloc[i]) or bool(exit_invalidation.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
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

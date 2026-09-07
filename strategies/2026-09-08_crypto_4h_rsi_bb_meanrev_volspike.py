"""Strategy: Crypto 4H RSI+Bollinger mean reversion with volume-spike confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-090),
sourced from https://edge-ledger.io/blog/mean-reversion-crypto-trading-strategy
("Mean Reversion Trading in Crypto: Finding Overextended Moves Before They
Snap Back"). Concrete rules quoted from the source:

    "Use the 4-hour chart with these indicators: RSI(14) -- Look for
    readings below 25 (oversold) or above 80 (overbought). Bollinger
    Bands(20, 2.5) -- Wait for price to close outside the bands. A valid
    signal requires both conditions to be true simultaneously."

    "Entry Rules: Price closes below the lower Bollinger Band AND RSI < 25
    -> Long entry. Enter on the next candle's open after confirmation."

    "Exit Rules: Take profit when price returns to the 20-period moving
    average (the Bollinger midline)."

    "Refining the Entry With Volume: Volume spike confirmation -- require
    the trigger candle's volume to exceed 1.5x the 20-period average. A
    move that touches the extreme without volume is often a continuation,
    not an exhaustion."

Distinct from the already-tested daily-bar RSI(14)+Bollinger-Bands(20,2std)
mean-reversion (2026-09-04-067, rejected) by (a) using the 4-HOUR timeframe
(source's own explicit crypto-specific recommendation, exploiting a faster
overreaction/snap-back cycle than daily bars capture), (b) wider Bollinger
bands (2.5 std vs 2.0), tighter RSI threshold (25 vs 30), and (c) adding
the source's own volume-spike confirmation filter (candle volume >= 1.5x
its own 20-period average) meant to distinguish exhaustion from
continuation.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series

Note: this repo's data/loaders.py load_crypto defaults to 1-HOUR bars (not
4-hour) over the multi-year backtest window used by validation/grid_test.py
-- rather than adding new interval-fetching plumbing, this strategy is
tested on the 1h bars grid_test.py already provides, with the caveat that
this is faster-timescale data than the source's own 4h recommendation
(the RSI/BB window parameters below are in units of 1h bars, not 4h bars).
Equity data via yfinance does not support intraday history over this
repo's multi-year window, so this strategy is crypto-only.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.5,
    rsi_window: int = 14,
    rsi_oversold: float = 25.0,
    vol_window: int = 20,
    vol_spike_ratio: float = 1.5,
    max_hold_bars: int = 120,
) -> pd.Series:
    """Return a {0,1} long/flat position series (bar granularity = price_df's own)."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    lower_band = sma - bb_std * std

    rsi = _rsi(close, rsi_window)
    avg_vol = volume.rolling(vol_window).mean()
    vol_spike = volume >= (vol_spike_ratio * avg_vol)

    signal_bar = (close < lower_band) & (rsi < rsi_oversold) & vol_spike.fillna(False)
    # "Enter on the next candle's open after confirmation" -- approximate
    # by entering the bar AFTER the signal bar (using close-to-close returns,
    # consistent with this repo's existing shift(1) exposure convention).
    entry = signal_bar.shift(1).fillna(False)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = 0
    for i in range(n):
        if in_pos:
            held = i - entry_idx
            exit_signal = (not pd.isna(sma.iloc[i])) and close.iloc[i] >= sma.iloc[i]
            if exit_signal or held >= max_hold_bars:
                in_pos = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted bar-over-bar returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    bar_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * bar_ret
    return strategy_ret

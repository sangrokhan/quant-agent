"""Strategy: Selling-Climax Volume Reversal (Wyckoff-style capitulation bottom).

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Per a Google AI-overview summary of "Strategy Rules and Mechanics" for a
selling-climax volume reversal (Smart Money/Trading Philosophy channels
cited): identify trend bottoms when extreme trading volume accompanies a
sharp sell-off from the lows. Source's own disclosed rule set: (1) Prior
Downtrend -- the market must be in a clear, sustained downward move (here:
close below its own rolling SMA(trend_window)); (2) The Climax Bar -- an
unusually tall candle (elevated true range) with a volume spike (source's
own multiplier: 3-5x the average volume) and a long lower wick, closing
well above its absolute low (source's own "absorption" signature: large
institutional buying absorbing panic selling from weak hands, i.e. close
in the upper portion of the bar's own range); (3) Entry Trigger -- buy at
the open of the next candle after the climax bar closes, or wait for a
confirming bullish candle (this implementation uses the confirming-candle
variant: entry requires the NEXT bar's close to be higher than the climax
bar's close); (4) Take Profit -- mean-revert toward a short-term moving
average (source's own disclosed exit) or a max_hold_days time-stop
backstop.

First "climax volume"/selling-climax-reversal strategy in this repo (0
prior matches for "climax volume" or "exhaustion gap" in
strategies_index.jsonl) -- distinct from prior volume-based entries
(OBV, Klinger, Chaikin, Force Index, Demand Index, etc., all momentum/flow
oscillators) since this is a single-bar EVENT-DETECTION pattern (a specific
candle's volume+range+wick shape) gated by a prior downtrend, not a
continuous oscillator.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    volume_avg_window: int = 20,
    volume_spike_mult: float = 3.0,
    range_avg_window: int = 20,
    range_spike_mult: float = 1.5,
    close_position_min: float = 0.6,
    exit_ma_window: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """0/1 long-only position series.

    Entry: (1) close below rolling SMA(trend_window) -- prior downtrend;
    (2) that bar's volume >= volume_spike_mult * its own rolling average
    volume, AND that bar's true range >= range_spike_mult * its own
    rolling average true range -- the "climax bar"; (3) that bar's close
    sits in the upper `close_position_min` fraction of its own high-low
    range (absorption/long-lower-wick signature); (4) confirmed by the
    NEXT bar closing higher than the climax bar's close (entry on that
    next bar). Exit: close reaches back up to a short-term moving average
    (`exit_ma_window`), or `max_hold_days` bars elapsed.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    trend_down = close < close.rolling(trend_window).mean()

    avg_volume = volume.rolling(volume_avg_window).mean()
    volume_spike = volume >= volume_spike_mult * avg_volume

    true_range = (high - low).abs()
    avg_range = true_range.rolling(range_avg_window).mean()
    range_spike = true_range >= range_spike_mult * avg_range

    bar_range = (high - low).replace(0, np.nan)
    close_position = (close - low) / bar_range
    absorption = close_position >= close_position_min

    climax_bar = (trend_down & volume_spike & range_spike & absorption).fillna(False)

    # Confirmation: next bar's close > climax bar's close, entry on that
    # next bar (shift climax_bar forward by 1 to align with the
    # confirming bar's own index).
    climax_prev = climax_bar.shift(1).fillna(False)
    confirm = close > close.shift(1)
    entry_trigger = (climax_prev & confirm).to_numpy()

    exit_ma = close.rolling(exit_ma_window).mean()
    exit_trigger = (close >= exit_ma).fillna(False).to_numpy()

    n = len(close)
    position = np.zeros(n)
    in_pos = False
    bars_held = 0
    for i in range(n):
        if in_pos:
            bars_held += 1
            if exit_trigger[i] or bars_held >= max_hold_days:
                in_pos = False
                bars_held = 0
            else:
                position[i] = 1.0
        else:
            if entry_trigger[i]:
                in_pos = True
                bars_held = 0
                position[i] = 1.0

    return pd.Series(position, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    volume_avg_window: int = 20,
    volume_spike_mult: float = 3.0,
    range_avg_window: int = 20,
    range_spike_mult: float = 1.5,
    close_position_min: float = 0.6,
    exit_ma_window: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        trend_window=trend_window,
        volume_avg_window=volume_avg_window,
        volume_spike_mult=volume_spike_mult,
        range_avg_window=range_avg_window,
        range_spike_mult=range_spike_mult,
        close_position_min=close_position_min,
        exit_ma_window=exit_ma_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret

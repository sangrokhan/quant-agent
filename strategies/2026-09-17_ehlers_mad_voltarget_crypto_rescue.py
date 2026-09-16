"""Strategy: Ehlers MAD (Moving Average Difference) zero-line crossover
base signal, WITH an inverse-volatility position-sizing overlay + no-trade
rebalance buffer -- crypto rescue attempt.

Direct fix for 2026-09-17-061's decisive crypto rejection (BTC/USDT MDD
58.7%, ETH/USDT MDD 43.5%, both ~2x the 25% threshold, at full binary
exposure). Same MAD zero-line crossover base signal (see
strategies/2026-09-17_ehlers_mad_zeroline_crossover.py and
knowledge_base/strategies_log.jsonl id=2026-09-17-061/062 for the indicator
source: TASC October 2021, John F. Ehlers, "Cycle/Trend Analytics And The
MAD Indicator", https://traders.com/documentation/feedbk_docs/2021/10/traderstips.html),
but the discrete {0,1} position is replaced with a continuous inverse-vol
scaled exposure (this repo's standard fix pattern, per
strategies/2026-09-07_sma_trend_voltarget_buffer.py, itself sourced from
https://blave.org/agent/en/learn/vol_targeting):

    scale = clip(target_vol / realized_vol, upper=vol_cap)
    desired_size = base_signal * scale

with a no-trade rebalance buffer band (only actually change the held
position when the newly desired size differs from the currently held size
by more than `rebalance_buffer`) to avoid the transaction-cost blowup this
repo has repeatedly observed when a continuous size is naively churned
every day on vol noise.

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (continuous held size)
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


def _mad(close: pd.Series, short_length: int, long_length: int) -> pd.Series:
    short_avg = close.rolling(short_length).mean()
    long_avg = close.rolling(long_length).mean()
    return 100.0 * (short_avg - long_avg) / long_avg


def _mad_base_signal(
    price_df: pd.DataFrame,
    short_length: int,
    long_length: int,
    trend_window: int,
    min_hold_days: int,
    max_hold_days: int,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    mad = _mad(close, short_length, long_length)
    trend_sma = close.rolling(trend_window).mean()
    raw_long_signal = (mad > 0) & (close > trend_sma)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            want_flat = (not bool(raw_long_signal.iloc[i])) and held >= min_hold_days
            if want_flat or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(raw_long_signal.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position.astype(float)


def _compute_desired_size(
    price_df: pd.DataFrame,
    short_length: int = 6,
    long_length: int = 18,
    trend_window: int = 100,
    min_hold_days: int = 5,
    max_hold_days: int = 40,
    vol_window: int = 20,
    target_vol: float = 0.30,
    vol_cap: float = 1.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    base_signal = _mad_base_signal(
        price_df, short_length, long_length, trend_window, min_hold_days, max_hold_days
    )

    log_ret = np.log(close / close.shift(1))
    realized_vol = log_ret.rolling(vol_window, min_periods=vol_window).std() * (252 ** 0.5)

    raw_scale = target_vol / realized_vol
    raw_scale = raw_scale.replace([np.inf, -np.inf], np.nan).clip(upper=vol_cap)
    raw_scale = raw_scale.fillna(0.0)

    desired = base_signal * raw_scale
    return desired.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    short_length: int = 6,
    long_length: int = 18,
    trend_window: int = 100,
    min_hold_days: int = 5,
    max_hold_days: int = 40,
    vol_window: int = 20,
    target_vol: float = 0.30,
    vol_cap: float = 1.0,
    rebalance_buffer: float = 0.10,
) -> pd.Series:
    """Return the continuous (buffered) held position-size series."""
    desired = _compute_desired_size(
        price_df,
        short_length=short_length,
        long_length=long_length,
        trend_window=trend_window,
        min_hold_days=min_hold_days,
        max_hold_days=max_hold_days,
        vol_window=vol_window,
        target_vol=target_vol,
        vol_cap=vol_cap,
    )

    held = pd.Series(index=desired.index, dtype=float)
    prev_held = 0.0
    desired_vals = desired.to_numpy()
    held_vals = np.empty(len(desired_vals), dtype=float)
    for i in range(len(desired_vals)):
        d = desired_vals[i]
        if abs(d - prev_held) > rebalance_buffer:
            prev_held = d
        held_vals[i] = prev_held
    held[:] = held_vals
    return held


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change()
    position = generate_signals(price_df, **kwargs)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret.fillna(0.0)

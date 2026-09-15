"""Strategy: Realized-Volatility Ratio EXHAUSTION SPIKE mean-reversion
(long-only "buy the panic" variant, companion to the compression/breakout
strategy 2026-09-16-083 tested earlier this cron trigger).

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Per the same Google AI-overview source used for 2026-09-16-083 (FlashAlpha/
LuxAlgo cited): the RV Ratio = RV_short(10d) / RV_long(90d) identifies
volatility regimes. This iteration tests the OTHER half of the source's
own two-sided setup: RV_ratio >> 1 (source's own threshold example: > 2.0
to 2.5, or the 95th percentile of the ratio's own rolling history) is an
"exhaustion spike" -- short-term panic/forced-liquidation volatility that
is unsustainably higher than the broader regime, and mean-reverts back
toward baseline. The source's own construction is a SHORT-volatility trade
(short the asset that spiked, betting vol crashes back down); this
long-only adaptation (per SAFETY.md, no short-selling in this repo) instead
BUYS THE PANIC: enter long when RV_ratio spikes above `spike_threshold`
AND price has fallen over the preceding `panic_lookback` days (confirms
the vol spike was driven by a selloff, not a melt-up), betting on the
mean-reversion bounce as the panic-driven vol spike fades back toward
baseline. Exit when RV_ratio reverts back below `exit_threshold` (vol has
normalized) or a `max_hold_days` time-stop.

Distinct from 2026-09-16-083 (compression regime + breakout, RV_ratio LOW)
and from this repo's 4 prior single-window vol-percentile-rank compression
entries -- this is the spike/panic-mean-reversion half of the same
two-timescale RV-ratio construction, a fundamentally different regime
(high vs. low RV_ratio) with a fundamentally different trade direction
(fade the spike vs. confirm the breakout).

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


def _annualized_realized_vol(close: pd.Series, window: int) -> pd.Series:
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(window).std() * np.sqrt(252)


def generate_signals(
    price_df: pd.DataFrame,
    rv_short_window: int = 10,
    rv_long_window: int = 90,
    spike_threshold: float = 2.0,
    exit_threshold: float = 1.2,
    panic_lookback: int = 5,
    panic_drop_threshold: float = -0.03,
    max_hold_days: int = 15,
) -> pd.Series:
    """0/1 long-only position series.

    Entry: RV_ratio = RV_short / RV_long spikes above `spike_threshold`
    AND the `panic_lookback`-day cumulative return is below
    `panic_drop_threshold` (confirms the spike is panic-selloff-driven, not
    a melt-up). Exit: RV_ratio reverts back below `exit_threshold`, or
    `max_hold_days` bars elapsed.
    """
    df = _prep(price_df)
    close = df["close"]

    rv_short = _annualized_realized_vol(close, rv_short_window)
    rv_long = _annualized_realized_vol(close, rv_long_window)
    rv_ratio = rv_short / rv_long.replace(0, np.nan)

    panic_return = close.pct_change(panic_lookback)

    entry_trigger = (
        (rv_ratio > spike_threshold) & (panic_return < panic_drop_threshold)
    ).fillna(False).to_numpy()
    exit_trigger = (rv_ratio < exit_threshold).fillna(False).to_numpy()

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
    rv_short_window: int = 10,
    rv_long_window: int = 90,
    spike_threshold: float = 2.0,
    exit_threshold: float = 1.2,
    panic_lookback: int = 5,
    panic_drop_threshold: float = -0.03,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        rv_short_window=rv_short_window,
        rv_long_window=rv_long_window,
        spike_threshold=spike_threshold,
        exit_threshold=exit_threshold,
        panic_lookback=panic_lookback,
        panic_drop_threshold=panic_drop_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret

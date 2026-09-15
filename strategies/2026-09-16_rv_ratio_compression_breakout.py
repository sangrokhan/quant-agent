"""Strategy: Realized-Volatility Ratio (short/long RV) regime + breakout
confirmation, proxying the variance-risk-premium/vol-compression trade
without options-implied-vol data.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Per a Google AI-overview summary (FlashAlpha/LuxAlgo cited) of how to trade
volatility-risk-premium-style compression/expansion cycles on equities
WITHOUT options-implied-volatility data (this repo has no options chain):
compute RV_short = annualized realized vol over a fast rolling window
(10-day) and RV_long = annualized realized vol over a slow rolling window
(90-day, the "historical baseline normal" per the source). The ratio
RV_ratio = RV_short / RV_long identifies regime: RV_ratio < 0.70 means the
stock is in a "quiet/compressed" regime (short-term vol has collapsed well
below its own baseline -- the source's own rule: potential expansion
ahead, i.e. a volatility-compression setup that historically precedes a
breakout). This implementation trades the LONG side of that setup: enter
long when RV_ratio drops below `compression_threshold` AND price
subsequently breaks out above its own `breakout_window`-day high (the
source's implied "wait for the expansion to actually start, don't buy the
quiet period itself" confirmation), exit when RV_ratio reverts back above
`exit_threshold` (vol has normalized/expanded back to baseline, the edge
of the setup has played out) or a max_hold_days time-stop.

Distinct from the 4 prior "volatility compression" entries in this repo
(Parkinson percentile-rank mean-reversion 2026-09-09-028/027; GAPO
log-range gauge 2026-09-08-050; two no-candidate iterations) since none of
those use a RATIO of two DIFFERENT-window realized-vol measures as the
regime signal (all prior compression entries use a single-window vol
measure's own percentile rank) -- this is a two-timescale relative
volatility-regime construction, closer in spirit to how a VIX-term-structure
trade would identify "vol is unusually low vs. its own history" without
requiring an actual implied-vol series.

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
    compression_threshold: float = 0.70,
    exit_threshold: float = 1.0,
    breakout_window: int = 20,
    max_hold_days: int = 40,
) -> pd.Series:
    """0/1 long-only position series.

    Entry: RV_ratio = RV_short / RV_long drops below `compression_threshold`
    (vol-compression regime -- quiet before expansion) AND close makes a
    new `breakout_window`-day high on the same or a later bar while still
    in the compression regime (confirms the expansion has actually begun).
    Exit: RV_ratio reverts above `exit_threshold` (vol normalized/expanded
    back to baseline) or `max_hold_days` bars have elapsed.
    """
    df = _prep(price_df)
    close = df["close"]

    rv_short = _annualized_realized_vol(close, rv_short_window)
    rv_long = _annualized_realized_vol(close, rv_long_window)
    rv_ratio = rv_short / rv_long.replace(0, np.nan)

    is_compressed = rv_ratio < compression_threshold
    breakout = close >= close.rolling(breakout_window).max()

    entry_trigger = (is_compressed & breakout).fillna(False).to_numpy()
    exit_trigger = (rv_ratio > exit_threshold).fillna(False).to_numpy()

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
    compression_threshold: float = 0.70,
    exit_threshold: float = 1.0,
    breakout_window: int = 20,
    max_hold_days: int = 40,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        rv_short_window=rv_short_window,
        rv_long_window=rv_long_window,
        compression_threshold=compression_threshold,
        exit_threshold=exit_threshold,
        breakout_window=breakout_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret

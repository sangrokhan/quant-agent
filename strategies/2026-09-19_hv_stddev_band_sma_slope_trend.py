"""Strategy: Slope-confirmed SMA(100) trend-following, gated by Kaufman's
"Is It Too Volatile To Trade?" historical-volatility std-dev-band filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-006):
Per Cesar Alvarez's "Avoiding Volatile Trades"
(https://alvarezquanttrading.com/blog/avoiding-volatile-trades/, read via
browser_exec after web_search DDGS backend returned unusable results this
iteration), summarizing Perry Kaufman's TASC July 2022 article "Is It Too
Volatile To Trade?": a trend-following entry (today's 100-day SMA greater
than each of the prior 5 days' 100-day SMA -- a slope-confirmed uptrend,
avoiding single-day whipsaws) is additionally gated by requiring the
current 20-day historical volatility (HV) to be BELOW its own trailing
2-year median plus `entry_std_mult` standard deviations (Kaufman's
proposed "too volatile to trade" ceiling); the exit rule symmetrically
adds an early-exit trigger when HV rises above the median plus
`exit_std_mult` standard deviations (a wider band than the entry ceiling,
per Alvarez's own tested asymmetric bands). Alvarez's own portfolio-level
finding was that this exact rule reduces MDD but also reduces CAR --
his optimization additionally found that entry std-dev bands BELOW ZERO
(i.e. requiring HV under the median, not just under median+Nstd) gave the
best drawdown-reduction results, which this repo tests directly via a
negative `entry_std_mult`.

This is a genuinely distinct construction from the already-tested
2026-09-03-021 (SMA(50)/SMA(200) golden-cross, gated by a realized-vol
PERCENTILE-RANK <= 0.5 within a 200-bar window) via: (a) a different trend
signal (5-day-confirmed single SMA(100) slope, not a dual-SMA crossover),
and (b) a different volatility-gate construction (median + N standard
deviations of a 2-year trailing HV distribution, with separate/asymmetric
entry and exit thresholds, rather than a simple percentile-rank cutoff).

Interface contract for validators (see validation/validators.py) and
grid_test.py: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments.
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


def _historical_vol(close: pd.Series, window: int) -> pd.Series:
    """Annualized realized volatility (std of daily log returns * sqrt(252))."""
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(window).std() * (252 ** 0.5)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    slope_confirm_days: int = 5,
    hv_window: int = 20,
    hv_lookback: int = 504,  # ~2 trading years
    entry_std_mult: float = 0.0,
    exit_std_mult: float = 2.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    # Slope confirmation: today's SMA greater than EACH of the prior
    # slope_confirm_days days' SMA values (i.e. min over that lookback of
    # sma_diff > 0).
    sma_diff = sma.diff()
    slope_up = sma_diff.rolling(slope_confirm_days).min() > 0
    slope_down = sma_diff.rolling(slope_confirm_days).max() < 0
    slope_up = slope_up.fillna(False)
    slope_down = slope_down.fillna(False)

    hv = _historical_vol(close, hv_window)
    hv_median = hv.rolling(hv_lookback, min_periods=hv_window).median()
    hv_std = hv.rolling(hv_lookback, min_periods=hv_window).std()

    entry_ceiling = hv_median + entry_std_mult * hv_std
    exit_ceiling = hv_median + exit_std_mult * hv_std

    hv_ok_entry = (hv < entry_ceiling).fillna(False)
    hv_too_high_exit = (hv > exit_ceiling).fillna(False)

    entry_trigger = (slope_up & hv_ok_entry).fillna(False)
    exit_trigger = (slope_down | hv_too_high_exit).fillna(True)

    in_position = False
    pos_vals = [0] * len(close)
    entry_vals = entry_trigger.values
    exit_vals = exit_trigger.values
    for i in range(len(pos_vals)):
        if in_position:
            if exit_vals[i]:
                in_position = False
                pos_vals[i] = 0
            else:
                pos_vals[i] = 1
        else:
            if entry_vals[i]:
                in_position = True
                pos_vals[i] = 1
            else:
                pos_vals[i] = 0
    position = pd.Series(pos_vals, index=close.index, dtype=int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

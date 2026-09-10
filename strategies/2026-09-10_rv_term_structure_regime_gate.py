"""Strategy: Realized-volatility term-structure (RV7/RV30 ratio) regime
gate on a trend-following long, applicable to BOTH equity and crypto since
it's constructed purely from price data (no VIX/implied-vol dependency).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-121):
Per a Google AI-overview synthesis (LuxAlgo sourced) of a crypto realized-
volatility (RV) term-structure trading strategy: compute short-horizon
realized vol (RV7, 7-day rolling annualized std of log returns) and
long-horizon realized vol (RV30, 30-day). RV_ratio = RV7/RV30.
- Contango (RV_ratio < 0.90): calm market, recent price action stable
  relative to baseline -- source frames this as the "normal", tradeable
  regime.
- Backwardation (RV_ratio > 1.05): short-term vol spiking above the
  baseline, signaling active market shock/stress/liquidation cascade --
  source frames this as a regime to AVOID being long through.

This repo has several prior VIX-based implied-vol term-structure
strategies (2026-09-04-157, 2026-09-05-028, 2026-09-06-127, all
near-miss/rejected) but those are equity-only by construction (no crypto
VIX analogue). This is the first REALIZED-vol term-structure strategy in
this repo -- pure price-derived RV7/RV30, so unlike the VIX-family
strategies it's directly computable and testable on crypto too, closing
that gap. Operationalized as a regime gate on a simple trend-following
long: hold long only while close > SMA(trend_window) AND RV_ratio is in
the "calm" contango regime (< contango_threshold); exit (flatten) if
either the trend breaks or RV_ratio spikes into backwardation
(> backwardation_threshold), or a max_hold_days time-stop backstop.

Signal logic
------------
- RV_short = rolling std of daily log returns over rv_short_window,
  annualized (* sqrt(252)).
- RV_long = rolling std of daily log returns over rv_long_window,
  annualized.
- RV_ratio = RV_short / RV_long.
- Entry (long): close > SMA(trend_window) AND RV_ratio < contango_threshold.
- Exit: close <= SMA(trend_window) (trend break) OR
  RV_ratio > backwardation_threshold (vol-spike risk-off) OR a
  max_hold_days time-stop.
- Flat otherwise; long-only, no shorting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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
    rv_short_window: int = 7,
    rv_long_window: int = 30,
    contango_threshold: float = 0.90,
    backwardation_threshold: float = 1.05,
    trend_window: int = 50,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    log_ret = np.log(close / close.shift(1))

    rv_short = log_ret.rolling(rv_short_window).std() * np.sqrt(252.0)
    rv_long = log_ret.rolling(rv_long_window).std() * np.sqrt(252.0)
    rv_ratio = (rv_short / rv_long.replace(0.0, np.nan)).fillna(1.0)

    trend_sma = close.rolling(trend_window).mean()
    uptrend = (close > trend_sma).fillna(False)
    calm_regime = (rv_ratio < contango_threshold).fillna(False)
    stress_regime = (rv_ratio > backwardation_threshold).fillna(False)

    entry_ok = (uptrend & calm_regime).fillna(False)
    exit_trigger = ((~uptrend) | stress_regime).fillna(False)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_day = -1

    entry_arr = entry_ok.values
    exit_arr = exit_trigger.values

    for i in range(n):
        if in_position:
            if bool(exit_arr[i]) or (i - entry_day) >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue
        if bool(entry_arr[i]):
            in_position = True
            entry_day = i
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

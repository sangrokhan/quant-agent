"""Strategy: Close Location Value (CLV) single-bar extreme mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-064):
Close Location Value, CLV = ((Close-Low)-(High-Close))/(High-Low), measures
where within a single bar's range the close occurred: CLV=+1 means the
close was at the bar's high (full buying pressure/"accumulation"), CLV=-1
means the close was at the bar's low (full selling pressure/
"distribution") -- per Investopedia's Close Location Value definition and
VT Markets' Accumulation/Distribution Indicator guide.

This is deliberately NOT the cumulative Accumulation/Distribution LINE
already tested in this repo (2026-09-04-047, a running total of
CLV*volume, used as a TREND-confirmation slope filter) -- this strategy
uses the raw, non-cumulative, single-bar CLV value directly as a
short-horizon MEAN-REVERSION oversold/overbought oscillator: a sharp
single-bar close-at-the-low (CLV below a negative extreme_threshold) after
a down day, occurring in an established uptrend (close>SMA(trend_window)),
signals capitulation/an overextended one-bar selling climax worth fading
long; exit when CLV recovers above a recovery_threshold (buying pressure
returning) or the trend filter breaks or a max_hold_days time-stop.

Distinct construction rationale: the cumulative A/D line integrates CLV
over the ENTIRE price history (a trend-confirmation tool by design,
smoothing out single-bar noise); this strategy instead treats an
individual bar's raw CLV extreme as a short-term reversal trigger --
mechanically closer to the IBS (Internal Bar Strength) family already
tested in this repo, but IBS = (Close-Low)/(High-Low) in [0,1] while CLV
= ((Close-Low)-(High-Close))/(High-Low) in [-1,1] is a different (though
related) normalization -- IBS ignores the symmetric high-side term that
CLV explicitly subtracts, giving CLV a different sensitivity profile
especially for bars where the close is near the midpoint.

Source: https://www.investopedia.com/terms/c/close_location_value.asp ;
https://www.vtmarkets.com/en-eu/discover/accumulation-distribution/

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
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


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    extreme_threshold: float = -0.6,
    recovery_threshold: float = 0.2,
    max_hold_days: int = 8,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    n = len(close)

    range_ = (high - low).replace(0, np.nan)
    clv = ((close - low) - (high - close)) / range_
    clv = clv.fillna(0.0)

    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False)

    entry = (clv <= extreme_threshold) & uptrend
    exit_recovery = clv >= recovery_threshold

    entry_arr = entry.to_numpy(dtype=bool)
    exit_arr = exit_recovery.to_numpy(dtype=bool)
    uptrend_arr = uptrend.to_numpy(dtype=bool)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_arr[i]) or (not bool(uptrend_arr[i])) or held >= max_hold_days:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if bool(entry_arr[i]):
                in_position = True
                entry_idx = i
                position[i] = 1
            else:
                position[i] = 0

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret

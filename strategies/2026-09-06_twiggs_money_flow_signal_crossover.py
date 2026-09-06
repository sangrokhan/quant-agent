"""Strategy: Twiggs Money Flow (TMF) signal-line crossover, trend-gated.

Hypothesis (see knowledge_base id 2026-09-06-143):
Per quantifiedstrategies.com's Twiggs Money Flow article
(https://www.quantifiedstrategies.com/twiggs-money-flow/):
"The indicator generally generates two types of signals: the zero-line
crossover signal and the divergence signal... Some traders and analysts may
add an EMA of the indicator as a signal line and use the signal line
crossovers as their buy and sell signals."

This tests the SIGNAL-LINE crossover variant specifically (an EMA of TMF
itself as a trigger line), which is distinct from the already-tested
zero-line-crossover variant (2026-09-05-002, id in this repo). Gated by a
close > SMA(trend_window) uptrend filter (standard practice throughout this
repo's strategy family, not source-specific) since TMF alone is a
volume-pressure oscillator, not a directional trend filter.

Twiggs Money Flow (Colin Twiggs, derived from Chaikin Money Flow):
TRCL_t = (2*Close_t - TrueLow_t - TrueHigh_t) / (TrueHigh_t - TrueLow_t)
  where TrueHigh_t = max(High_t, Close_{t-1}), TrueLow_t = min(Low_t, Close_{t-1})
  (this is what makes TMF gap-aware vs CMF's plain High/Low range).
TMF_t = 100 * EMA(Volume_t * TRCL_t, tmf_window) / EMA(Volume_t, tmf_window)

Signal logic
------------
- TMF: as above, tmf_window-period EMA smoothing (default 21, source's
  standard).
- Signal line: EMA(TMF, signal_window) (default 9).
- Entry (long): TMF crosses above its signal line AND close > SMA(trend_window)
  (uptrend filter).
- Exit: TMF crosses back below its signal line, OR the trend filter breaks
  (close <= SMA(trend_window)), OR a max_hold_days time-stop.

Interface contract (see validation/validators.py, validation/grid_test.py):
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


def _tmf(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    prev_close = close.shift(1)
    true_high = pd.concat([high, prev_close], axis=1).max(axis=1)
    true_low = pd.concat([low, prev_close], axis=1).min(axis=1)
    true_range = (true_high - true_low).replace(0.0, np.nan)
    trcl = (2 * close - true_low - true_high) / true_range
    trcl = trcl.fillna(0.0)
    weighted_vol = volume * trcl
    ema_weighted = weighted_vol.ewm(span=window, min_periods=window, adjust=False).mean()
    ema_vol = volume.ewm(span=window, min_periods=window, adjust=False).mean().replace(0.0, np.nan)
    tmf = 100.0 * ema_weighted / ema_vol
    return tmf.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    tmf_window: int = 21,
    signal_window: int = 9,
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]
    n = len(close)

    tmf = _tmf(high, low, close, volume, tmf_window)
    signal = tmf.ewm(span=signal_window, min_periods=signal_window, adjust=False).mean()

    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    tmf_above = tmf > signal
    entry = tmf_above & (~tmf_above.shift(1).fillna(False)) & uptrend.fillna(False)
    exit_cross = (~tmf_above) & tmf_above.shift(1).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            trend_break = not bool(uptrend.iloc[i])
            if bool(exit_cross.iloc[i]) or trend_break or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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

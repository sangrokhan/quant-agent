"""Strategy: Chande & Kroll Dynamic Momentum Index (DMI) -- adaptive-lookback
RSI variant, oversold/overbought threshold-cross entry/exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-024):
Per Google AI-overview synthesis of LuxAlgo/TradingPedia/positioned.app DMI
explainers (visited this iteration): Tushar Chande & Stanley Kroll's Dynamic
Momentum Index is a variable-length RSI whose lookback period ADAPTS to
recent volatility -- shrinking toward a minimum (source: ~5 bars) when
short-term volatility spikes (letting the oscillator react instantly to
sharp moves), and stretching toward a maximum (source: ~30 bars) when
volatility is calm (filtering out noise). The adaptive period is computed
as a base period (14) divided by a relative-volatility-index derived from
the ratio of a short-window stdev to its own longer-window average stdev.
Trading rule (source's own disclosed thresholds): DMI dropping below the
oversold level (30) then crossing back above it signals a long entry; DMI
crossing back below the overbought level (70) after being above it signals
an exit (mirrored short entry, not used here -- long-only).

Novelty vs existing repo entries: this is the first ADAPTIVE-LOOKBACK RSI
variant in this repo (distinct from all fixed-period RSI variants already
tested, and distinct from Jurik/RSX DEMA-smoothed RSI 2026-09-05-087 which
alters the SMOOTHING method not the LOOKBACK LENGTH itself).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _dynamic_rsi(
    close: pd.Series,
    base_period: int,
    vol_short_window: int,
    vol_long_window: int,
    min_period: int,
    max_period: int,
) -> pd.Series:
    """Chande & Kroll Dynamic Momentum Index: RSI computed with a per-bar
    adaptive lookback period, derived from base_period / relative_volatility,
    clipped to [min_period, max_period]."""
    log_ret = np.log(close / close.shift(1))
    vol_short = log_ret.rolling(vol_short_window).std()
    vol_long = vol_short.rolling(vol_long_window).mean()
    relative_vol = (vol_short / vol_long.replace(0.0, np.nan)).fillna(1.0)
    relative_vol = relative_vol.replace([np.inf, -np.inf], 1.0).fillna(1.0)

    adaptive_period = (base_period / relative_vol).round().clip(
        lower=min_period, upper=max_period
    ).fillna(base_period).astype(int)

    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    n = len(close)
    dmi = pd.Series(np.nan, index=close.index)

    # Precompute RSI for every distinct period value actually used, then
    # select per-bar from the matching series (efficient vs per-bar looping
    # while still respecting the per-bar adaptive period).
    distinct_periods = sorted(set(int(p) for p in adaptive_period.dropna().unique()))
    rsi_by_period = {}
    for p in distinct_periods:
        p = max(p, 2)
        avg_gain = gain.ewm(alpha=1.0 / p, min_periods=p, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / p, min_periods=p, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0.0, np.nan)
        rsi_p = 100 - (100 / (1 + rs))
        rsi_by_period[p] = rsi_p.fillna(50.0)

    period_vals = adaptive_period.values
    dmi_vals = np.full(n, np.nan)
    for i in range(n):
        p = int(period_vals[i]) if not np.isnan(period_vals[i]) else base_period
        p = max(p, 2)
        series_p = rsi_by_period.get(p)
        if series_p is None:
            avg_gain = gain.iloc[: i + 1].ewm(alpha=1.0 / p, min_periods=p, adjust=False).mean()
            avg_loss = loss.iloc[: i + 1].ewm(alpha=1.0 / p, min_periods=p, adjust=False).mean()
            rs = avg_gain.iloc[-1] / avg_loss.iloc[-1] if avg_loss.iloc[-1] != 0 else np.nan
            dmi_vals[i] = 100 - (100 / (1 + rs)) if not np.isnan(rs) else 50.0
        else:
            dmi_vals[i] = series_p.iloc[i]

    return pd.Series(dmi_vals, index=close.index).fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    base_period: int = 14,
    vol_short_window: int = 5,
    vol_long_window: int = 30,
    min_period: int = 5,
    max_period: int = 30,
    oversold_level: float = 30.0,
    overbought_level: float = 70.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: DMI crosses back above oversold_level after having been
    below it. Exit: DMI crosses back below overbought_level after having
    been above it, or a max_hold_days time-stop.
    """
    df = _prep(price_df)
    close = df["close"]

    dmi = _dynamic_rsi(close, base_period, vol_short_window, vol_long_window, min_period, max_period)

    entry_signal = (dmi > oversold_level) & (dmi.shift(1) <= oversold_level)
    exit_signal = (dmi < overbought_level) & (dmi.shift(1) >= overbought_level)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_i = None
    n = len(close)

    for i in range(n):
        if in_position:
            position.iloc[i] = 1
            hold_len = i - entry_i
            if bool(exit_signal.iloc[i]) or hold_len >= max_hold_days:
                in_position = False
                entry_i = None
        else:
            if bool(entry_signal.iloc[i]) if pd.notna(entry_signal.iloc[i]) else False:
                in_position = True
                entry_i = i
                position.iloc[i] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

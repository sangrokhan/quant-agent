"""Strategy: Parabolic SAR applied to RSI (oscillator-domain PSAR reversal),
RSI>50 long-only filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-093),
sourced from https://kr.tradingview.com/scripts/crypto-strategy/
("Parabolic RSI Strategy [ChartPrime x PineIndicators]": "A custom
Parabolic SAR function tracks momentum within the RSI, not price. This
allows the system to capture RSI trend reversals more responsively... Long
Entry: Triggered when the SAR flips below the RSI line... Optional RSI
filter ensures that Long entries only occur above a minimum RSI (e.g.
50)."):

First strategy in this repo to apply the Parabolic SAR algorithm to an
OSCILLATOR series (RSI) rather than to price itself -- structurally
distinct from every prior Parabolic-SAR-on-price strategy tested here
(2026-09-04-042 plain SAR+SMA filter, 2026-09-05-017 Gann HiLo+SAR,
2026-09-05-062 DPO+DM+SAR triple confirmation, 2026-09-05-082 ADX
divergence+SAR). The economic rationale (per source): applying SAR's
acceleration/extreme-point mechanics to RSI's own momentum trajectory
should flag RSI trend reversals earlier/more responsively than a simple
RSI threshold or moving-average crossover, since SAR's parabolic
acceleration adapts its own sensitivity as the RSI trend persists.

Signal logic
------------
- RSI(rsi_window) computed on close (standard Wilder RSI).
- Parabolic SAR algorithm applied to the RSI series itself (RSI value
  substituted for both "high" and "low" since RSI is a single-value
  series, not OHLC) -- standard Wilder SAR state machine (acceleration
  factor starts at af_start, increments by af_step on each new extreme
  point, capped at af_max).
- Long entry: SAR (in RSI-space) flips from above-RSI to below-RSI (i.e.
  bullish flip) AND RSI > rsi_min_filter (default 50, source's stated
  optional filter).
- Exit: SAR flips back above the RSI line (bearish flip), or a
  max_hold_days time-stop (repo standard safety valve).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _sar_on_series(
    series: pd.Series, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2
) -> pd.Series:
    """Standard Wilder Parabolic SAR state machine applied to a single
    scalar series (the series value plays the role of both the "high" and
    "low" of each bar, since there is no OHLC structure for an oscillator).
    Returns the SAR value series (same index as input)."""
    vals = series.values
    n = len(vals)
    sar = np.full(n, np.nan)

    first_valid = series.first_valid_index()
    if first_valid is None:
        return pd.Series(sar, index=series.index)
    start_i = series.index.get_loc(first_valid)
    if start_i + 1 >= n:
        return pd.Series(sar, index=series.index)

    # Initialize: assume uptrend, SAR starts at the first value, EP is next value
    is_uptrend = True
    af = af_start
    ep = vals[start_i]
    cur_sar = vals[start_i]
    sar[start_i] = cur_sar

    for i in range(start_i + 1, n):
        v = vals[i]
        if np.isnan(v):
            sar[i] = cur_sar
            continue

        prev_sar = cur_sar
        new_sar = prev_sar + af * (ep - prev_sar)

        if is_uptrend:
            if v < new_sar:
                # flip to downtrend
                is_uptrend = False
                new_sar = ep
                ep = v
                af = af_start
            else:
                if v > ep:
                    ep = v
                    af = min(af + af_step, af_max)
        else:
            if v > new_sar:
                # flip to uptrend
                is_uptrend = True
                new_sar = ep
                ep = v
                af = af_start
            else:
                if v < ep:
                    ep = v
                    af = min(af + af_step, af_max)

        cur_sar = new_sar
        sar[i] = cur_sar

    return pd.Series(sar, index=series.index)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    af_start: float = 0.02,
    af_step: float = 0.02,
    af_max: float = 0.2,
    rsi_min_filter: float = 50.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_window)
    sar = _sar_on_series(rsi, af_start, af_step, af_max)

    bullish_flip = (rsi > sar) & (rsi.shift(1) <= sar.shift(1))
    bearish_flip = (rsi < sar) & (rsi.shift(1) >= sar.shift(1))

    entry_signal = (bullish_flip & (rsi > rsi_min_filter)).fillna(False).values
    exit_signal = bearish_flip.fillna(False).values

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if exit_signal[i] or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_signal[i]:
                in_position = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

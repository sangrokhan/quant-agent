"""Strategy: Ehlers Deviation-Scaled Moving Average (DSMA) percent-band
mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per John Ehlers' Deviation-Scaled Moving Average (TASC July 2018), as
disclosed at https://www.prorealcode.com/prorealtime-indicators/deviation-scaled-moving-average-dsma/
(exact formula) and https://www2.wealth-lab.com/WL5Wiki/TASCJul2018.ashx
(exact strategy rule): DSMA is an adaptive EMA whose alpha term rapidly
scales with volatility -- a 2-pole SuperSmoother filter is applied to a
2-bar-differenced close series ("Zeros"), producing "Filt"; a rolling RMS
(root-mean-square, a standard-deviation-style scale) of Filt over `period`
bars normalizes it; alpha1 = abs(ScaledFilt) * 5 / period becomes the
adaptive EMA smoothing factor (default period=40). The source's own
disclosed strategy (Wealth-Lab Traders' Tip, explicitly framed as
"counter-trend for kicks"): buy at next open when today's closing price
crosses a percentage BELOW the 40-period DSMA; exit (sell) when close
crosses a percentage ABOVE the DSMA (percentages can be asymmetric). First
DSMA strategy in this repo, distinct from KAMA/FRAMA/VIDYA (other adaptive
moving averages already tested) since DSMA's adaptation mechanism is
uniquely based on a SuperSmoother-filtered, RMS-normalized "standard
deviations from the mean" scale rather than an efficiency ratio or fractal
dimension.

Signal logic
------------
- DSMA(period) computed exactly per the source's disclosed formula (2-pole
  SuperSmoother on the 2-bar close difference, RMS-normalized, adaptive
  alpha).
- Entry (long): close crosses below DSMA * (1 - entry_pct) (source's own
  percentage-band mean-reversion trigger).
- Exit: close crosses above DSMA * (1 + exit_pct), OR a max_hold_days
  time-stop backstop (added safety net; the source's own rule has no
  explicit time-stop).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _dsma(close: pd.Series, period: int) -> pd.Series:
    n = len(close)
    close_vals = close.values.astype(float)

    a1 = math.exp(-1.414 * math.pi / (0.5 * period))
    b1 = 2 * a1 * math.cos(1.414 * 180 * math.pi / 180 / (0.5 * period))
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    zeros = np.full(n, np.nan)
    for i in range(2, n):
        zeros[i] = close_vals[i] - close_vals[i - 2]

    filt = np.zeros(n)
    for i in range(2, n):
        z_i = zeros[i] if not np.isnan(zeros[i]) else 0.0
        z_im1 = zeros[i - 1] if (i - 1 >= 2 and not np.isnan(zeros[i - 1])) else 0.0
        filt[i] = c1 * (z_i + z_im1) / 2 + c2 * filt[i - 1] + c3 * filt[i - 2]

    dsma = np.full(n, np.nan)
    for i in range(period, n):
        window = filt[i - period + 1 : i + 1]
        rms = math.sqrt(np.mean(window ** 2)) if np.mean(window ** 2) > 0 else 1e-9
        scaled_filt = filt[i] / rms if rms > 0 else 0.0
        alpha1 = min(abs(scaled_filt) * 5 / period, 1.0)
        prev_dsma = dsma[i - 1] if i > period and not np.isnan(dsma[i - 1]) else close_vals[i]
        dsma[i] = alpha1 * close_vals[i] + (1 - alpha1) * prev_dsma

    return pd.Series(dsma, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 40,
    entry_pct: float = 0.02,
    exit_pct: float = 0.02,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    dsma = _dsma(close, period)
    lower_band = dsma * (1 - entry_pct)
    upper_band = dsma * (1 + exit_pct)

    entry_signal = (close < lower_band) & (close.shift(1) >= lower_band.shift(1))
    exit_signal = (close > upper_band) & (close.shift(1) <= upper_band.shift(1))

    entry_signal = entry_signal.fillna(False)
    exit_signal = exit_signal.fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_days = 0
    entry_vals = entry_signal.values
    exit_vals = exit_signal.values

    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            exit_now = exit_vals[i] or (hold_days >= max_hold_days)
            if exit_now:
                in_pos = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_vals[i]:
                in_pos = True
                hold_days = 0
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 40,
    entry_pct: float = 0.02,
    exit_pct: float = 0.02,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        period=period,
        entry_pct=entry_pct,
        exit_pct=exit_pct,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0)
    return strat_ret

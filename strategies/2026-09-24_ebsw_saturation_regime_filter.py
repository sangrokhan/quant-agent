"""Strategy: Ehlers Even Better Sinewave (EBSW) saturation-persistence
regime filter -- a distinct technique from this repo's 2 prior EBSW
strategies (plain zero-line crossover timing, and a continuous z-score
sizing dial).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-030):
Per LuxAlgo's Even-better Sinewave library page
(https://www.luxalgo.com/library/indicator/even-better-sinewave/, read via
browser_exec): "Saturation: the wave holding at or beyond the Saturation
Level for the required bars confirms an established trend; ... Regime
filter: saturated stretches argue for trend tactics and against fading the
wave's extremes; clean undulation argues the reverse." This reframes EBSW
not as a cycle-timing oscillator (its usual zero-cross use, already
rejected in 2026-09-06-117 for this repo) but as a REGIME DETECTOR: when
the normalized wave pins near +1 for several consecutive bars, the market
has left its cycling/ranging mode and entered a persistent uptrend --
distinct construction from the already-tested zero-cross timing signal
(2026-09-06-117, rejected) and the continuous sizing dial (2026-09-14-194,
accepted as a CONTINUOUS exposure scaler, not a discrete regime gate).

EBSW formula (Ehlers, "Cycle Analytics for Traders", confirmed across
sources): 2-pole high-pass filter (cutoff = duration bars) on close, then
2-pole SuperSmoother (critical period = smooth_period) on the high-passed
series, then Wave = 3-bar SMA of smoothed series, Power = 3-bar SMA of
smoothed^2, EBSW = Wave / sqrt(Power) (normalized, roughly bounded -1..+1).

Signal logic
------------
- Compute EBSW(duration, smooth_period).
- Trend regime confirmed (long) when EBSW >= saturation_level for at least
  saturation_bars consecutive bars.
- Long entry: regime confirmation bar (the saturation_bars-th consecutive
  pinned bar) AND close > SMA(trend_window) (long-term uptrend gate, this
  repo's standard fix pattern for raw oscillator signals).
- Exit: EBSW drops back below saturation_level (saturation ending -- the
  trend regime the wave was confirming has broken), OR close < trend SMA
  (regime flip), OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1} position series
    generate_returns(price_df, **params) -> pd.Series daily strategy returns
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


def _high_pass_filter(price: np.ndarray, duration: int) -> np.ndarray:
    """Ehlers 2-pole high-pass filter with cutoff period = duration."""
    n = len(price)
    hp = np.zeros(n)
    alpha1 = (math.cos(0.707 * 2 * math.pi / duration) + math.sin(0.707 * 2 * math.pi / duration) - 1) / math.cos(0.707 * 2 * math.pi / duration)
    for t in range(n):
        if t < 2:
            hp[t] = 0.0
            continue
        hp[t] = (
            (1 - alpha1 / 2) ** 2 * (price[t] - 2 * price[t - 1] + price[t - 2])
            + 2 * (1 - alpha1) * hp[t - 1]
            - (1 - alpha1) ** 2 * hp[t - 2]
        )
    return hp


def _supersmoother(price: np.ndarray, period: int) -> np.ndarray:
    """Ehlers 2-pole SuperSmoother filter."""
    n = len(price)
    filt = np.zeros(n)
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2.0 * a1 * math.cos(1.414 * math.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1.0 - c2 - c3
    for t in range(n):
        if t < 2:
            filt[t] = price[t]
            continue
        filt[t] = c1 * (price[t] + price[t - 1]) / 2.0 + c2 * filt[t - 1] + c3 * filt[t - 2]
    return filt


def _ebsw(close: pd.Series, duration: int = 40, smooth_period: int = 10) -> pd.Series:
    price = close.to_numpy(dtype=float)
    n = len(price)

    hp = _high_pass_filter(price, duration)
    smoothed = _supersmoother(hp, smooth_period)

    wave = np.zeros(n)
    power = np.zeros(n)
    ebsw = np.full(n, np.nan)
    for t in range(n):
        if t < 3:
            continue
        wave[t] = (smoothed[t] + smoothed[t - 1] + smoothed[t - 2]) / 3.0
        power[t] = (smoothed[t] ** 2 + smoothed[t - 1] ** 2 + smoothed[t - 2] ** 2) / 3.0
        if power[t] > 0:
            ebsw[t] = wave[t] / math.sqrt(power[t])
        else:
            ebsw[t] = 0.0

    return pd.Series(ebsw, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    duration: int = 40,
    smooth_period: int = 10,
    saturation_level: float = 0.9,
    saturation_bars: int = 5,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ebsw = _ebsw(close, duration=duration, smooth_period=smooth_period)
    pinned = ebsw >= saturation_level
    # Consecutive pinned-bar run length ending at each bar.
    run_len = pinned.groupby((~pinned).cumsum()).cumcount() + 1
    run_len = run_len.where(pinned, 0)

    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    regime_confirmed = (run_len == saturation_bars)  # fires once, on confirmation bar
    entry = regime_confirmed & uptrend.fillna(False)
    saturation_ending = ~pinned  # wave dropped back below saturation level
    exit_regime_flip = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(saturation_ending.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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

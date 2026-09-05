"""Strategy: Ehlers Decycler Oscillator countertrend mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-046):
John Ehlers' Decycler ("Decyclers", TASC Sept 2015) is built from a 2-pole
highpass filter: Decycler = Price - HP(Price, period), i.e. price with
cycles shorter than `period` bars removed, leaving a very-low-lag trend
line. The Decycler *Oscillator* is the percentage difference between two
Decyclers built with a fast and a slow highpass period -- when the fast
decycler pulls meaningfully away from the slow decycler, price has moved
too far too fast relative to its own smoothed trend and tends to snap
back. Per theindicatorlab.com's review (google search result, exact URL
paywalled/404 on direct fetch, hence fallback to the AI-overview/snippet
text captured from the SERP): "Long entry: Oscillator crosses above -50
after being below -80 (oversold condition). Short entry: Oscillator
crosses below +50 after being above +80" -- i.e. classic bounded
countertrend threshold-cross rule, analogous to how this repo already
trades MESA Stochastic (id=2026-09-04-118, rejected) and Fisher Transform
(id=2026-09-04-051) extremes, but on the Decycler construction, which is
novel in this repo (first Decycler-family strategy; the Roofing Filter
id=2026-09-05-012 and MESA Stochastic id=2026-09-04-118 use the same
underlying HP+SuperSmoother "Filt" building block but as a
trend-following crossover / a 0-1 smoothed stochastic, not this dual-HP
percentage-spread oscillator).

Honest gap: the source snippet only gives the -80/-50/+50/+80 threshold
levels, not the exact oscillator scaling formula. We reconstruct the
standard Ehlers Decycler Oscillator as
    DecyclerOsc_t = 100 * (Decycler_fast_t - Decycler_slow_t) / Price_t
and apply an `osc_scale` multiplier (tunable, default 20) to bring the
raw percentage spread into the -80..+80 range the source's fixed
thresholds assume, since raw percentage spreads on daily equity/crypto
bars are typically <1-2% while the source's thresholds are on a much
larger absolute scale (this rescaling is our own interpretation, flagged
here and in the knowledge base notes rather than silently assumed).

Signal logic
------------
- HP_fast = 2-pole highpass filter with period=hp_fast_period (shorter,
  more reactive).
- HP_slow = 2-pole highpass filter with period=hp_slow_period (longer,
  smoother trend baseline).
- Decycler_fast = close - HP_fast; Decycler_slow = close - HP_slow.
- osc = osc_scale * 100 * (Decycler_fast - Decycler_slow) / close.
- Long entry: osc crosses above -50 after having been below -80 in the
  last lookback_extreme bars (oversold snapback).
- Short-equivalent (we go flat, long-only per repo convention): exit when
  osc crosses below +50 after having been above +80, OR a max_hold_days
  time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _highpass_2pole(close: np.ndarray, period: int) -> np.ndarray:
    n = len(close)
    rad = 0.707 * 2.0 * math.pi / period
    cos_rad = math.cos(rad)
    alpha1 = (cos_rad + math.sin(rad) - 1.0) / cos_rad if cos_rad != 0 else 0.0

    hp = np.zeros(n)
    for i in range(2, n):
        hp[i] = (
            (1 - alpha1 / 2.0) ** 2 * (close[i] - 2 * close[i - 1] + close[i - 2])
            + 2 * (1 - alpha1) * hp[i - 1]
            - (1 - alpha1) ** 2 * hp[i - 2]
        )
    return hp


def _decycler_oscillator(
    close: pd.Series, hp_fast_period: int, hp_slow_period: int, osc_scale: float
) -> pd.Series:
    c = close.to_numpy(dtype=float)
    hp_fast = _highpass_2pole(c, hp_fast_period)
    hp_slow = _highpass_2pole(c, hp_slow_period)
    decycler_fast = c - hp_fast
    decycler_slow = c - hp_slow
    with np.errstate(divide="ignore", invalid="ignore"):
        osc = osc_scale * 100.0 * (decycler_fast - decycler_slow) / c
    osc = np.nan_to_num(osc, nan=0.0, posinf=0.0, neginf=0.0)
    return pd.Series(osc, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    hp_fast_period: int = 30,
    hp_slow_period: int = 60,
    osc_scale: float = 20.0,
    oversold_extreme: float = -80.0,
    oversold_exit: float = -50.0,
    overbought_extreme: float = 80.0,
    overbought_exit: float = 50.0,
    lookback_extreme: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series (long-only countertrend)."""
    df = _prep(price_df)
    close = df["close"]

    osc = _decycler_oscillator(close, hp_fast_period, hp_slow_period, osc_scale)

    was_oversold = osc.rolling(lookback_extreme, min_periods=1).min().shift(1) < oversold_extreme
    entry = (osc > oversold_exit) & (osc.shift(1) <= oversold_exit) & was_oversold.fillna(False)

    was_overbought = osc.rolling(lookback_extreme, min_periods=1).max().shift(1) > overbought_extreme
    exit_signal = (osc < overbought_exit) & (osc.shift(1) >= overbought_exit) & was_overbought.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret

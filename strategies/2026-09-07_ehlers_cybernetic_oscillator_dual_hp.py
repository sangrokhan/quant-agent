"""Strategy: Ehlers Cybernetic Oscillator dual-timescale highpass-ROC trend
confirmation (TASC June 2025, via financial-hacker.com's "The Cybernetic
Oscillator" write-up).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-002):
John Ehlers' Cybernetic Oscillator swing-trading system smooths price with
a short lowpass filter, then applies a 2-pole highpass filter at TWO
different cutoff lengths (a short one capturing swings, a long one
capturing the underlying trend), and looks at the momentum (2-bar rate of
change) of each highpass-filtered series. Going long only when BOTH the
short-cutoff and long-cutoff highpass momentum are simultaneously positive
requires agreement between the short-term swing and the long-term trend
before committing, which should reduce whipsaw versus either signal alone.
Per the source's own SPY 2009-2025 backtest (Zorro platform, in-sample
optimized parameters): ~180 trades, 60% win rate, profit factor 2 (numbers
from the article prose, not independently reproducible here since we don't
have the exact Zorro cost/leverage model, but directionally motivates
testing this exact rule on our own data/cost model).

Distinct from every other Ehlers-family strategy already tried in this repo
(Roofing Filter [2026-09-05-012], Decycler Oscillator [2026-09-05-046],
MESA Stochastic [2026-09-04-118], Trendflex [2026-09-06-112], Voss
Predictive Filter [2026-09-06-120], Ultimate Smoother [2026-09-05-066],
Center of Gravity [2026-09-04-124]) -- none of those use a DUAL-cutoff
highpass rate-of-change agreement rule; this is the first strategy in this
repo requiring two different-timescale highpass-filtered momentum signals
to agree before entry.

Signal logic
------------
- Lowpass-smooth close with an EMA(smooth_len) (source's `Smooth`, a
  SuperSmoother in the original -- EMA is a standard, readily-available
  approximation with a similar effect: attenuate high-frequency noise
  before highpass filtering).
- Apply Ehlers' standard 2-pole highpass filter to the smoothed series at
  two cutoff lengths: `short_hp_len` and `long_hp_len`.
- ROC_short = HP_short[t] - HP_short[t-2]; ROC_long = HP_long[t] - HP_long[t-2]
  (source's own 2-bar rate-of-change; the "2" is fixed in the source code).
- Entry (long): not currently long, AND ROC_short > 0 AND ROC_long > 0.
- Exit: currently long AND (ROC_short < 0 OR ROC_long < 0) (source's own
  rule: exit as soon as either timescale's momentum turns negative).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _ehlers_highpass_2pole(price: pd.Series, length: int) -> pd.Series:
    """Ehlers' standard 2-pole highpass filter (as used in his EasyLanguage
    code and reproduced across his TASC articles, e.g. the Roofing Filter's
    highpass stage).
    """
    p = price.to_numpy(dtype=float)
    n = len(p)
    hp = np.zeros(n)

    angle = 0.707 * 2 * math.pi / length
    alpha1 = (math.cos(angle) + math.sin(angle) - 1) / math.cos(angle)

    a = (1 - alpha1 / 2) ** 2
    b = 2 * (1 - alpha1)
    c = (1 - alpha1) ** 2

    for i in range(n):
        if i < 2 or np.isnan(p[i]) or np.isnan(p[i - 1]) or np.isnan(p[i - 2]):
            hp[i] = 0.0
            continue
        hp[i] = a * (p[i] - 2 * p[i - 1] + p[i - 2]) + b * hp[i - 1] - c * hp[i - 2]

    return pd.Series(hp, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    smooth_len: int = 20,
    short_hp_len: int = 55,
    long_hp_len: int = 156,
    roc_lag: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    lp = close.ewm(span=smooth_len, adjust=False).mean()

    hp_short = _ehlers_highpass_2pole(lp, short_hp_len)
    hp_long = _ehlers_highpass_2pole(lp, long_hp_len)

    roc_short = hp_short - hp_short.shift(roc_lag)
    roc_long = hp_long - hp_long.shift(roc_lag)

    entry = (roc_short > 0) & (roc_long > 0)
    exit_cond = (roc_short < 0) | (roc_long < 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_cond.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret

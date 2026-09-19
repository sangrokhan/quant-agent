"""Strategy: Ehlers "One Euro Filter" adaptive low-lag smoother crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per John Ehlers' TASC article (as documented at
https://financial-hacker.com/the-one-euro-filter/, EasyLanguage->C port),
the "One Euro Filter" is a minimalistic adaptive low-latency smoother
derived from the 1-Euro-Filter (Casiez et al., https://gery.casiez.net/1euro/):
it EMA-smooths the bar-to-bar price delta (SmoothedDX), uses the absolute
smoothed delta to widen/narrow an adaptive cutoff period
(Cutoff = PeriodMin + Factor*|SmoothedDX|), and applies that adaptive
cutoff to a super-smoother-style EMA of price itself
(Alpha = 2*pi/(4*pi+Cutoff)). The filter tracks price with much less lag
than a fixed-period EMA/SMA during fast moves, while staying smooth during
quiet periods. This is a genuinely distinct adaptive-smoothing construction
from every other Ehlers filter already tested in this repo (SuperSmoother,
KAMA, Hull, PMA, LSMA, etc.) -- it adapts its own responsiveness to the
*rate of price change* rather than to cycle-period estimation or an
efficiency ratio.

One commenter on the source article flagged that the Factor parameter's
effect is scale-dependent (works differently for instruments with tiny
vs. large price deltas) -- we treat Factor as a tunable grid parameter
precisely to probe this sensitivity across QQQ/SPY/BTC/ETH.

Trading rule (adapted to a long/flat contract, consistent with this
repo's standard defensive pattern for adaptive-MA crossovers): long when
close crosses/stays above the One Euro Filter line AND close is above a
longer-term SMA trend filter (avoids whipsaws in choppy regimes, same
pattern used for KAMA/LSMA/PMA in this repo).

Signal logic
------------
- alpha1 = 2*pi / (4*pi + 10)  [fixed, per Ehlers' source]
- smoothed_dx[t] = alpha1*(close[t]-close[t-1]) + (1-alpha1)*smoothed_dx[t-1]
- cutoff[t] = period_min + factor * abs(smoothed_dx[t])
- alpha2[t] = 2*pi / (4*pi + cutoff[t])
- one_euro[t] = alpha2[t]*close[t] + (1-alpha2[t])*one_euro[t-1]
- trend_up = close > SMA(close, trend_window)
- Long (position=1) when close > one_euro AND trend_up; flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
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
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _one_euro_filter(close: pd.Series, period_min: float, factor: float) -> pd.Series:
    """Ehlers' One Euro Filter: adaptive low-lag smoother of close prices."""
    values = close.to_numpy(dtype=float)
    n = len(values)
    alpha1 = 2 * math.pi / (4 * math.pi + 10.0)

    smoothed_dx = np.zeros(n)
    smoothed = np.zeros(n)
    smoothed[0] = values[0]
    smoothed_dx[0] = 0.0

    for t in range(1, n):
        smoothed_dx[t] = alpha1 * (values[t] - values[t - 1]) + (1 - alpha1) * smoothed_dx[t - 1]
        cutoff = period_min + factor * abs(smoothed_dx[t])
        alpha2 = 2 * math.pi / (4 * math.pi + cutoff)
        smoothed[t] = alpha2 * values[t] + (1 - alpha2) * smoothed[t - 1]

    return pd.Series(smoothed, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    period_min: float = 10.0,
    factor: float = 2.0,
    trend_window: int = 100,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    one_euro = _one_euro_filter(close, period_min=period_min, factor=factor)
    above_filter = (close > one_euro).fillna(False)

    sma = close.rolling(trend_window).mean()
    trend_up = (close > sma).fillna(False)

    position = (above_filter & trend_up).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    period_min: float = 10.0,
    factor: float = 2.0,
    trend_window: int = 100,
) -> pd.Series:
    """Return the strategy's daily return series."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        period_min=period_min,
        factor=factor,
        trend_window=trend_window,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

"""Strategy: Ehlers MyRSI de-noised via Kendall-correlation Noise Elimination
Technology (NET), zero-line crossover trend signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-190):
Per "Petra on Programming: Get Rid of Noise"
(https://financial-hacker.com/petra-on-programming-get-rid-of-noise/,
covering John Ehlers' S&C December [2020] "Noise Elimination Technology"
article): fully disclosed C formulas for (1) MyRSI, a standard sum-of-ups
vs sum-of-downs RSI variant, and (2) NET, a Kendall-correlation-style
"denoising" transform that measures how monotonically a data series is
rising or falling over a trailing window (bounded -1..+1), used here on
MyRSI's own output rather than on raw price.

Source's own disclosed finding: applying the classic RSI overbought/
oversold threshold-crossing rule directly to the de-noised MyRSI was
"neither... a strong improvement over a simple lowpass filter strategy or
even... buy-and-hold" -- the source explicitly did NOT find a working
threshold-crossing rule and invited readers to find one. Rather than
reusing the source's own inconclusive overbought/oversold threshold rule,
this strategy operationalizes the article's clearly-stated economic
argument on its own terms: NET(MyRSI) is a *directional trend measure of
underlying momentum* (a Kendall-tau-like statistic of MyRSI's own path),
so a natural, distinct hypothesis is a simple zero-line trend-following
rule on it (long while NET(MyRSI) > 0, i.e. RSI's own trajectory is
net-rising over the window; flat otherwise) -- testing whether the
denoising itself (removing whipsaw from a raw momentum oscillator) adds
value as a trend filter, independent of the source's own inconclusive
mean-reversion attempt.

Signal logic
------------
- MyRSI(t) over `rsi_period`: CU = rolling sum of positive daily price
  changes over rsi_period+1 bars; CD = rolling sum of |negative changes|
  over the same window; MyRSI = (CU-CD)/(CU+CD) if CU+CD != 0 else 0.
  (Equivalent to a classic RSI rescaled to -1..+1 instead of 0..100.)
- NET(t) over `net_period`, applied to the trailing `net_period` values of
  MyRSI: for every pair of bars i>k within the window (i older, k newer),
  accumulate -sign(MyRSI[i]-MyRSI[k]); normalize by 0.5*net_period*
  (net_period-1). Bounded to [-1, +1]; positive = MyRSI has been net
  rising over the window (uptrend in momentum), negative = net falling.
- Long entry: NET(t) > 0. Flat: NET(t) <= 0.

Interface contract for validators (see validation/validators.py) and
grid_test (see validation/grid_test.py):
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).

Tunable params (all keyword args, per RESEARCH_LOOP.md Step 5 contract):
    rsi_period  (MyRSI lookback, default 14).
    net_period  (NET Kendall-correlation window, default 10; kept modest
        since NET is O(net_period^2) per bar).
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


def _my_rsi(close: pd.Series, rsi_period: int) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    cu = up.rolling(rsi_period + 1, min_periods=rsi_period + 1).sum()
    cd = down.rolling(rsi_period + 1, min_periods=rsi_period + 1).sum()
    denom = cu + cd
    rsi = (cu - cd) / denom.replace(0.0, np.nan)
    return rsi.fillna(0.0)


def _net(data: pd.Series, net_period: int) -> pd.Series:
    """Kendall-correlation-style Noise Elimination Technology transform.

    For each bar t, uses the trailing `net_period` values of `data`
    (index 0 = most recent). Num = -sum_{i>k} sign(Data[i]-Data[k]),
    Denom = 0.5*net_period*(net_period-1). Bounded to [-1, 1].
    """
    vals = data.to_numpy(dtype=float)
    m = len(vals)
    out = np.zeros(m)
    denom = 0.5 * net_period * (net_period - 1)

    for t in range(net_period - 1, m):
        window = vals[t - net_period + 1 : t + 1][::-1]  # window[0] = most recent (Data[0])
        num = 0.0
        for i in range(1, net_period):
            for k in range(0, i):
                diff = window[i] - window[k]
                num -= np.sign(diff)
        out[t] = num / denom if denom != 0 else 0.0

    return pd.Series(out, index=data.index)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    net_period: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    my_rsi = _my_rsi(close, rsi_period)
    net = _net(my_rsi, net_period)

    position = (net > 0).astype(int)
    warmup = rsi_period + net_period
    position.iloc[: min(warmup, len(position))] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    net_period: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(price_df, rsi_period=rsi_period, net_period=net_period)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

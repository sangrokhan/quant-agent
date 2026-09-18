"""Strategy: Kaufman "PJK Channels" Rule 3 -- trade-within-the-bands,
slope-gated mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-116):
Per Perry Kaufman's TASC 5/2025 article "PJK Channels" (EasyLanguage code
disclosed at https://traders.com/Documentation/FEEDbk_docs/2025/05/TradersTips.html,
read via browser_exec fallback after web_extract's DDGS backend could not
extract page content), the article discloses THREE distinct trading rules
built on the same regression-channel construction (Rule 0/1 = trend-only
slope follow; Rule 2 = breakout on band penetration; Rule 3 = trade *within*
the bands, entering near the band on the *same side as* the regression
slope and exiting at an inner Zone price target on the *opposite* band, or
immediately if the slope flips).

This is a genuinely different construction from the already-tested
2026-09-12-188 Kaufman "Inside Channel" (financial-hacker.com writeup),
which has NO slope-direction gate at all -- it enters near the lower band
regardless of trend direction and exits near the upper band regardless of
trend direction. PJK Rule 3 as literally coded by Kaufman himself requires:
  - Only take LONGS when slope > 0 (trading WITH the local trend direction,
    not pure countertrend reversion).
  - Long entry additionally requires close has pulled back to within Zone
    of the *lower* band (not the upper band) while the trend is still up --
    i.e. a pullback-in-uptrend entry, not a breakout.
  - Exit either at a Zone-distance-from-upper-band price target, OR
    immediately if slope turns negative (whichever the source's own code
    checks first, unconditionally, each bar).
This slope-gated pullback-in-trend construction is the source's own
distinguishing feature of Rule 3 vs Rule 2 (breakout) and vs the ungated
Inside Channel variant already tested. Long-only per repo convention.

Signal logic
------------
For each bar t, fit a rolling OLS regression over the trailing `period`
closes (oldest to newest, bar index 0..period-1):
  - slope[t], intercept[t] from OLS on close.
  - LinVal[t] (fitted regression value at the *last* bar of the window --
    "today's" trend value).
  - HighDev[t] = max deviation of any bar in the window above the fitted
    line (>=0), LowDev[t] = min deviation below (<=0) -- literal PJK
    "highdev"/"lowdev" loop.
  - upperband[t] = LinVal[t] + HighDev[t]; lowerband[t] = LinVal[t] + LowDev[t].
  - band_width[t] = upperband[t] - lowerband[t].
  - long_price_target[t] = lowerband[t] + zone * band_width[t]  (entry zone
    near the lower band).
  - short/exit_price_target[t] = upperband[t] - zone * band_width[t] (exit
    zone near the upper band).

Position update (long-only subset of Kaufman's Rule 3, EasyLanguage order
preserved -- exits checked before new entries each bar):
  - If currently long: exit (flatten) if close >= exit_price_target OR
    slope <= 0 (source checks "close >= pricetarget or slope < 0" for
    exiting a long -- we use <=0 to also flatten on a flat/zero slope).
  - If currently flat and slope > 0 and close <= long_price_target: enter
    long.
  - Otherwise carry forward the current position.

Interface contract for validators (see validation/validators.py) and
grid_test (see validation/grid_test.py):
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).

Tunable params (all keyword args, per RESEARCH_LOOP.md Step 5 contract):
    period (default 40)  -- regression/channel lookback in bars (PJK's own
                             default).
    zone   (default 0.20) -- inner-zone fraction of band width (PJK's own
                             default).
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


def _rolling_channel(close: pd.Series, period: int):
    """Vectorized-ish rolling OLS regression channel + slope.

    Returns (lin_val, high_dev, low_dev, slope) aligned to `close`'s index,
    NaN for bars before the first full window.
    """
    n = period
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    x_centered = x - x_mean
    denom = (x_centered ** 2).sum()

    vals = close.to_numpy(dtype=float)
    m = len(vals)
    lin_val = np.full(m, np.nan)
    high_dev = np.full(m, np.nan)
    low_dev = np.full(m, np.nan)
    slope_arr = np.full(m, np.nan)

    for t in range(n - 1, m):
        window = vals[t - n + 1 : t + 1]
        y_mean = window.mean()
        slope = (x_centered * (window - y_mean)).sum() / denom
        intercept = y_mean - slope * x_mean
        fitted = intercept + slope * x
        dev = window - fitted
        lin_val[t] = fitted[-1]
        high_dev[t] = max(dev.max(), 0.0)
        low_dev[t] = min(dev.min(), 0.0)
        slope_arr[t] = slope

    return (
        pd.Series(lin_val, index=close.index),
        pd.Series(high_dev, index=close.index),
        pd.Series(low_dev, index=close.index),
        pd.Series(slope_arr, index=close.index),
    )


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 40,
    zone: float = 0.20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    lin_val, high_dev, low_dev, slope = _rolling_channel(close, period)
    band_width = high_dev - low_dev  # low_dev <= 0, so this is >= 0
    upperband = lin_val + high_dev
    lowerband = lin_val + low_dev
    long_entry_target = lowerband + zone * band_width
    exit_target = upperband - zone * band_width

    position = pd.Series(0, index=close.index, dtype=int)
    pos = 0
    for i in range(len(close)):
        if np.isnan(lin_val.iloc[i]):
            position.iloc[i] = 0
            continue
        c = close.iloc[i]
        s = slope.iloc[i]
        if pos == 1:
            if c >= exit_target.iloc[i] or s <= 0:
                pos = 0
        else:
            if s > 0 and c <= long_entry_target.iloc[i]:
                pos = 1
        position.iloc[i] = pos

    return position.fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 40,
    zone: float = 0.20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(price_df, period=period, zone=zone)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

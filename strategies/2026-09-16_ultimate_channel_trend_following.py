"""Strategy: Ehlers Ultimate Channel + Ultimate Bands trend-following
(TASC May 2024), long-only, per the source's own disclosed trading rule.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per traders.com's exact disclosed EasyLanguage source (TASC May 2024
Traders' Tips, "Ultimate Channels And Ultimate Bands" by John F. Ehlers,
https://traders.com/Documentation/FEEDbk_docs/2024/05/TradersTips.html,
found via a systematic browser_exec scan of the TASC Traders' Tips archive
after web_search returned no useful results this iteration):

Ultimate Channel (Keltner-style): centerline = UltimateSmoother(close,
length); band half-width STR = UltimateSmoother(true_high - true_low,
str_length) (an UltimateSmoother-smoothed true range, an ATR analog);
UpperChnl/LowerChnl = centerline +/- num_strs * STR.

Ultimate Bands (Bollinger-style): centerline = UltimateSmoother(close,
length); SD = sqrt(rolling_mean((close - centerline)^2, length)) (std-dev
of price around the smoothed centerline, an SMA-std-dev analog);
UpperBand/LowerBand = centerline +/- num_sds * SD.

The Wealth-Lab Traders' Tips implementer directly quotes Ehlers' own
disclosed trading rule from the article: "hold a position in the direction
of the UltimateSmoother and exit that position when the price pops outside
the channel or band in the opposite direction." This strategy implements
that rule using the Ultimate Channel construction (selectable to use
Ultimate Bands instead via `use_bands`): long only when close >
UltimateSmoother centerline (i.e. "in the direction of the smoother"),
exit when close closes below the LOWER channel/band (price pops out
against the current long direction).

First Ultimate Channel/Ultimate Bands strategy in this repo -- distinct
from every prior Keltner/Bollinger-family entry since both centerline and
band-width use Ehlers' UltimateSmoother rather than SMA/EMA and raw
std-dev/ATR.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _ultimate_smoother(src: pd.Series, period: int) -> pd.Series:
    """Ehlers' UltimateSmoother (TASC Apr 2024): allpass minus highpass."""
    period = max(int(period), 1)
    a1 = math.exp(-1.414 * math.pi / period)
    c2 = 2.0 * a1 * math.cos(1.414 * math.pi / period)
    c3 = -a1 * a1
    c1 = (1.0 + c2 - c3) / 4.0

    vals = src.ffill().fillna(0.0).to_numpy()
    n = len(vals)
    us = np.zeros(n)
    for i in range(n):
        if i < 4:
            us[i] = vals[i]
        else:
            us[i] = (
                (1.0 - c1) * vals[i]
                + (2.0 * c1 - c2) * vals[i - 1]
                - (c1 + c3) * vals[i - 2]
                + c2 * us[i - 1]
                + c3 * us[i - 2]
            )
    return pd.Series(us, index=src.index)


def _ultimate_channel(
    high: pd.Series, low: pd.Series, close: pd.Series,
    length: int, str_length: int, num_strs: float,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    prev_close = close.shift(1)
    true_high = pd.concat([high, prev_close], axis=1).max(axis=1)
    true_low = pd.concat([low, prev_close], axis=1).min(axis=1)
    str_series = _ultimate_smoother(true_high - true_low, str_length)
    centerline = _ultimate_smoother(close, length)
    upper = centerline + num_strs * str_series
    lower = centerline - num_strs * str_series
    return centerline, upper, lower


def _ultimate_bands(
    close: pd.Series, length: int, num_sds: float
) -> tuple[pd.Series, pd.Series, pd.Series]:
    centerline = _ultimate_smoother(close, length)
    sq_dev = (close - centerline) ** 2
    sd = np.sqrt(sq_dev.rolling(length).mean())
    upper = centerline + num_sds * sd
    lower = centerline - num_sds * sd
    return centerline, upper, lower


def generate_signals(
    price_df: pd.DataFrame,
    use_bands: bool = False,
    length: int = 20,
    str_length: int = 20,
    num_strs: float = 1.0,
    num_sds: float = 1.0,
) -> pd.Series:
    """0/1 long-only position series, per Ehlers' own disclosed rule: hold
    a position in the direction of the UltimateSmoother, exit when price
    pops outside the channel/band in the opposite direction (i.e. closes
    below the lower band while long).
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    if use_bands:
        centerline, upper, lower = _ultimate_bands(close, length, num_sds)
    else:
        centerline, upper, lower = _ultimate_channel(high, low, close, length, str_length, num_strs)

    in_uptrend = close > centerline
    pop_below = close < lower

    in_uptrend_arr = in_uptrend.fillna(False).to_numpy()
    pop_below_arr = pop_below.fillna(False).to_numpy()

    n = len(close)
    position = np.zeros(n)
    in_pos = False
    for i in range(n):
        if in_pos:
            if pop_below_arr[i]:
                in_pos = False
            else:
                position[i] = 1.0
        else:
            if in_uptrend_arr[i]:
                in_pos = True
                position[i] = 1.0

    return pd.Series(position, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    use_bands: bool = False,
    length: int = 20,
    str_length: int = 20,
    num_strs: float = 1.0,
    num_sds: float = 1.0,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        use_bands=use_bands,
        length=length,
        str_length=str_length,
        num_strs=num_strs,
        num_sds=num_sds,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret

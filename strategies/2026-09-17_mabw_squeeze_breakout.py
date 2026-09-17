"""Strategy: Apirine Moving Average Band Width (MABW) squeeze breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-163):
Vitali Apirine's two-part article (TASC Jul/Aug 2021, "Moving Average
Bands" + "Moving Average Band Width", source: Traders.com Aug 2021
Traders' Tips, TradeStation EasyLanguage code read this iteration) builds
bands around a long EMA (MA1) whose width is the deviation of a SHORT EMA
(MA2) from MA1 (i.e. bands widen/narrow based on how far a fast-moving
average has recently strayed from the slow one), NOT a Bollinger-style
price standard deviation. BandWidth = (Upper-Lower)/MA1*100 measures
relative band narrowness; a fresh low in BandWidth (a "squeeze", MA2
tracking very close to MA1, meaning short-term price action has been
unusually calm relative to the long-term trend) followed by a price
breakout above the UpperBand should mark the start of a new directional
move breaking out of consolidation. This band construction (deviation of
a fast-EMA/slow-EMA spread, not price stdev) is novel in this repo,
distinct from all Bollinger-Band / Keltner-Channel / ATR-based squeeze
strategies already tested (which all use price-range or price-stdev-based
band width).

Formula (per source)
---------------------
- MA1 = EMA(Close, periods1) [long/slow], MA2 = EMA(Close, periods2) [short/fast]
- Dst = MA1 - MA2
- Dev = sqrt(rolling_mean(Dst^2, periods2)) * mltp
- UpperBand = MA1 + Dev, LowerBand = MA1 - Dev
- BandWidth = (UpperBand - LowerBand) / MA1 * 100
- LLV = rolling_min(BandWidth, periods1) [tracks the recent low/squeeze level]

Signal logic (adaptation to a testable trading rule; source's own articles
are indicator-only, no explicit trading rule)
------------------------------------------------------------------------
- Squeeze detection: BandWidth is within `squeeze_pct` of its own
  `periods1`-bar rolling low (LLV) -- i.e. currently near its narrowest in
  recent history.
- Entry (long): a squeeze was active within the last `lookback_days` bars,
  AND close breaks above UpperBand today (breakout confirmation).
- Exit: close falls back below MA1 (midline), OR after `max_hold_days`.
- No short leg.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    periods1: int = 50,
    periods2: int = 10,
    mltp: float = 1.0,
    squeeze_pct: float = 0.1,
    lookback_days: int = 5,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ma1 = close.ewm(span=periods1, adjust=False).mean()
    ma2 = close.ewm(span=periods2, adjust=False).mean()
    dst = ma1 - ma2
    dev = ((dst ** 2).rolling(periods2).mean() ** 0.5) * mltp
    upper_band = ma1 + dev
    lower_band = ma1 - dev

    band_width = (upper_band - lower_band) / ma1 * 100
    llv = band_width.rolling(periods1).min()

    is_squeeze = band_width <= llv * (1 + squeeze_pct)
    squeeze_recent = is_squeeze.rolling(lookback_days).max().astype(bool)

    breakout = close > upper_band
    entry = squeeze_recent & breakout

    exit_signal = close < ma1

    warmup = periods1 + periods2

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if i < warmup:
            position.iloc[i] = 0
            continue
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
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

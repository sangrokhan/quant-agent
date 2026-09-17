"""Strategy: Money Flow Oscillator (MFO) Persistence-Confirmation
(Vitali Apirine, "The Money Flow Oscillator", TASC October 2015), read this
iteration via browser_exec at
https://traders.com/Documentation/FEEDbk_docs/2015/10/TradersTips.html
(exact TradeStation EasyLanguage indicator/function/strategy code disclosed
directly in the Traders' Tips section, after web_search DDGS backend
errored on prior queries this run -- direct traders.com archive URL
navigation to a previously-unvisited month, discovered by walking forward
from adjacent known TASC months already in this repo's
visited_urls.jsonl ledger).

Hypothesis (see knowledge_base/strategies_log.jsonl entry for this id):
Apirine's MFO computes a multiplier MLTP = ((High-PrevLow) - (PrevHigh-Low))
/ ((High-PrevLow) + (PrevHigh-Low)) -- a symmetric, bounded [-1,1] measure
of whether TODAY's high/low range extended MORE beyond yesterday's low
(bullish, MLTP>0) or yesterday's high (bearish, MLTP<0) -- multiplies it by
volume to get money-flow-volume (MFV), then sums MFV over `length` bars and
normalizes by the sum of the (always-positive) volume-based denominator,
giving an oscillator around zero. Distinct from every other money-flow
construction in this repo (Chaikin Money Flow uses close-position-within-
range not a two-bar high/low comparison; Money Flow Index is RSI-style on
typical-price*volume; Klinger uses trend/volume-force logic) because MFO's
multiplier compares TODAY's range extension against BOTH yesterday's high
AND low simultaneously in a single symmetric ratio, not a single-bar
range-position or price-direction measure. The article's OWN strategy rule
(disclosed directly, not a third-party reconstruction) requires MFO to
stay on one side of zero for `confirm_bars` CONSECUTIVE bars before
entering -- a persistence-confirmation filter distinct from a simple
zero-cross, intended to avoid whipsaw on marginal readings. First Money
Flow Oscillator strategy in this repo. Long-only adaptation of the
source's long/short symmetric strategy.

Exact formula (from TASC Oct 2015 TradeStation EasyLanguage, as read this
iteration):
    Dvs = (High - PrevLow) + (PrevHigh - Low)
    MLTP = round(((High - PrevLow) - (PrevHigh - Low)) / Dvs, 2)  if Dvs!=0 else 0 (carries forward prior value in EasyLanguage's no-else branch, approximated here as 0 on the rare Dvs==0 bar)
    MFV = MLTP * Volume
    MFO = sum(MFV, length) / sum(Volume, length)

    UpCounter[t] = UpCounter[t-1]+1, DnCounter[t]=0   if MFO>0
    DnCounter[t] = DnCounter[t-1]+1, UpCounter[t]=0   if MFO<=0
    Long entry: UpCounter >= confirm_bars (persistence confirmation).
    Long exit (long-only adaptation of source's SellShort-on-DnCounter):
        DnCounter >= confirm_bars.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
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


def _mfo(df: pd.DataFrame, length: int) -> pd.Series:
    high, low, volume = df["high"], df["low"], df["volume"]
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    dvs = (high - prev_low) + (prev_high - low)
    numerator = (high - prev_low) - (prev_high - low)
    mltp = np.where(dvs != 0, np.round(numerator / dvs.replace(0.0, np.nan), 2), 0.0)
    mltp = pd.Series(mltp, index=df.index).fillna(0.0)

    mfv = mltp * volume
    mfo = mfv.rolling(length).sum() / volume.rolling(length).sum()
    return mfo


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 20,
    confirm_bars: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the MFO persistence-
    confirmation rule (long-only adaptation)."""
    df = _prep(price_df)
    n = len(df)

    mfo = _mfo(df, length)
    mfo_vals = mfo.values
    valid_vals = mfo.notna().values

    up_counter = 0
    dn_counter = 0
    position = np.zeros(n, dtype=int)
    in_long = False

    for i in range(n):
        if not valid_vals[i]:
            position[i] = 0
            continue
        if mfo_vals[i] > 0:
            up_counter += 1
            dn_counter = 0
        else:
            up_counter = 0
            dn_counter += 1

        if up_counter >= confirm_bars:
            in_long = True
        elif dn_counter >= confirm_bars:
            in_long = False

        position[i] = 1 if in_long else 0

    return pd.Series(position, index=df.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

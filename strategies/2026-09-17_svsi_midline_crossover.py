"""Strategy: Slow Volume Strength Index (SVSI) Midline Crossover
(Vitali Apirine, "The Slow Volume Strength Index", TASC June 2015; code
published in TASC August 2015 Traders' Tips), read this iteration via
browser_exec at
https://traders.com/Documentation/FEEDbk_docs/2015/08/TradersTips.html
(exact TradeStation EasyLanguage indicator+strategy code disclosed directly
in the Traders' Tips section, after web_search DDGS backend errored on
prior queries this run -- direct traders.com archive URL navigation to a
previously-unvisited month, discovered by walking forward from adjacent
known TASC months already in this repo's visited_urls.jsonl ledger).

Hypothesis (see knowledge_base/strategies_log.jsonl entry for this id):
Apirine's SVSI classifies EACH bar's ENTIRE volume as either "positive" (if
close is above a short EMA of close) or "negative" (if below), then applies
Wilder-style recursive RSI-like smoothing (a 1/14 smoothing factor,
hardcoded in the source's own EasyLanguage as `((AvgPosVol*13)+PosVolume)/14`
regardless of the `SmoothingLength` input, faithfully reproduced here) to
these positive/negative volume streams, and finally applies the RSI ratio
formula (`100 - 100/(1+SVS)`) to get a bounded [0,100] oscillator. This is
distinct from every prior volume-oscillator construction in this repo (OBV,
PVT, VPT, Klinger, Chaikin Money Flow, Twiggs Money Flow, Force Index) since
none binarize the ENTIRE bar's volume into a positive/negative bucket based
on a price-vs-EMA gate before applying RSI-style smoothing -- most others
weight volume by the SIZE of the price change, not a simple above/below-EMA
binary classification. First Slow Volume Strength Index (SVSI) strategy in
this repo. Long-only adaptation of the source's long/short symmetric
midline-crossover strategy.

Exact formula (from TASC Aug 2015 TradeStation EasyLanguage, as read this
iteration; `SmoothingLength` input is disclosed but the recursive update
itself is hardcoded to a 14-period Wilder smoothing factor in the source's
own code -- reproduced faithfully as `wilder_length=14` fixed, with
`smoothing_length` kept as a tunable seed-window parameter for the initial
SMA seed only, per the source's exact `if CurrentBar=1 then Average(...,
SmoothingLength)` vs `else ((Avg*13)+New)/14` structure):
    EMAValue = EMA(Close, ema_length)
    PosVolume[t] = Volume[t] if Close[t] > EMAValue[t] else 0
    NegVolume[t] = Volume[t] if Close[t] < EMAValue[t] else 0
    (both 0 if Close[t] == EMAValue[t])
    AvgPosVol[seed] = SMA(PosVolume, smoothing_length)  (seeded at bar 1)
    AvgNegVol[seed] = SMA(NegVolume, smoothing_length)
    AvgPosVol[t] = (AvgPosVol[t-1]*13 + PosVolume[t]) / 14   (t>seed)
    AvgNegVol[t] = (AvgNegVol[t-1]*13 + NegVolume[t]) / 14
    SVS = AvgPosVol / AvgNegVol (100 if AvgNegVol==0)
    SVSI = 100 - 100/(1+SVS)

Long entry: SVSI crosses above MidLine (50). Long exit (this iteration's
long-only adaptation of the source's SellShort-on-cross-under): SVSI
crosses below MidLine.

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


def _svsi(df: pd.DataFrame, ema_length: int, smoothing_length: int) -> pd.Series:
    close = df["close"]
    volume = df["volume"]
    n = len(df)

    ema_value = close.ewm(span=ema_length, adjust=False).mean()

    pos_volume = np.where(close.values > ema_value.values, volume.values, 0.0)
    neg_volume = np.where(close.values < ema_value.values, volume.values, 0.0)

    avg_pos = np.full(n, np.nan)
    avg_neg = np.full(n, np.nan)

    if n <= smoothing_length:
        return pd.Series(np.full(n, 50.0), index=df.index)

    seed_idx = smoothing_length - 1
    avg_pos[seed_idx] = pos_volume[: smoothing_length].mean()
    avg_neg[seed_idx] = neg_volume[: smoothing_length].mean()

    for i in range(seed_idx + 1, n):
        avg_pos[i] = (avg_pos[i - 1] * 13 + pos_volume[i]) / 14.0
        avg_neg[i] = (avg_neg[i - 1] * 13 + neg_volume[i]) / 14.0

    svs = np.where(avg_neg != 0, avg_pos / np.where(avg_neg != 0, avg_neg, 1.0), 100.0)
    svsi = 100.0 - (100.0 / (1.0 + svs))
    svsi[:seed_idx] = 50.0
    return pd.Series(svsi, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    ema_length: int = 6,
    smoothing_length: int = 14,
    mid_line: float = 50.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the SVSI midline-crossover rule."""
    df = _prep(price_df)
    n = len(df)

    svsi = _svsi(df, ema_length, smoothing_length)
    cross_over = (svsi > mid_line) & (svsi.shift(1) <= mid_line)
    cross_under = (svsi < mid_line) & (svsi.shift(1) >= mid_line)

    co_vals = cross_over.values
    cu_vals = cross_under.values
    valid_vals = svsi.notna().values

    position = np.zeros(n, dtype=int)
    in_long = False
    for i in range(n):
        if not valid_vals[i]:
            position[i] = 0
            continue
        if co_vals[i]:
            in_long = True
        elif cu_vals[i]:
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

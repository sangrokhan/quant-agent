"""Strategy: Williams Accumulation/Distribution (WAD) bullish divergence.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-089):
Per QuantifiedStrategies.com's article on the Williams Accumulation
Distribution (https://www.quantifiedstrategies.com/williams-accumulation-distribution/),
quoting Larry Williams' own 1995 Las Vegas seminar verbatim: "My formula
is to first ask if the price closed up or down for the day. If up, I will
then subtract the low from the close and add this amount of
'accumulation' into a cumulative line or index. If prices close down for
the day, I will subtract the close from the high and subtract this value
from the cumulative index... I look for divergence between price and the
A/D. If the price is up and not matched by A/D, a sell is coming. If the
price breaks to a new low and A/D does not, then a buy is coming."

This is a precise, directly implementable rule (unlike most divergence
indicators on this site, the source discloses BOTH the exact indicator
formula AND the exact signal-generation logic in the creator's own words,
with no numeric threshold gap to fill in).

WAD formula (no volume, unlike the standard Chaikin A/D Line):
    True Range Low (TRL)  = min(Low_t, Close_{t-1})
    True Range High (TRH) = max(High_t, Close_{t-1})
    if Close_t > Close_{t-1}: AD_move = Close_t - TRL   (accumulation, add)
    if Close_t < Close_{t-1}: AD_move = Close_t - TRH   (distribution, subtract -- note this is negative since Close_t < TRH)
    if Close_t == Close_{t-1}: AD_move = 0
    WAD_t = WAD_{t-1} + AD_move   (cumulative)

Signal (bullish divergence only, long-only per SAFETY.md):
    Price makes a new N-bar low (close/low at a rolling-window minimum)
    while WAD does NOT make a corresponding new N-bar low over the same
    window -> accumulation is happening beneath a falling price ->
    long entry. Exit when price makes a new N-bar high without WAD
    confirming (bearish divergence, the source's mirror-image sell
    signal) or a max_hold_days time-stop.

First Williams Accumulation Distribution strategy in this repo -- distinct
from the standard (volume-weighted) Chaikin Accumulation/Distribution Line
already tested, since WAD deliberately excludes volume and uses a
True-Range-anchored move calculation instead.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _williams_ad(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)

    trl = pd.concat([low, prev_close], axis=1).min(axis=1)
    trh = pd.concat([high, prev_close], axis=1).max(axis=1)

    up = close > prev_close
    down = close < prev_close

    ad_move = pd.Series(0.0, index=close.index)
    ad_move[up] = (close - trl)[up]
    ad_move[down] = (close - trh)[down]
    # first bar has no prev_close reference; treat as 0 move
    ad_move.iloc[0] = 0.0

    wad = ad_move.cumsum()
    return wad


def generate_signals(
    price_df: pd.DataFrame,
    divergence_window: int = 20,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    divergence_window: rolling lookback (bars) used to define a "new low"
        / "new high" for both price and WAD when checking for divergence
        (source gives no numeric window; grid-tested tunable).
    max_hold_days: fixed time-stop safety net (source's bearish-divergence
        exit signal is the primary exit; this bounds worst-case holds).
    """
    df = _prep(price_df)
    close = df["close"]
    wad = _williams_ad(df)

    price_new_low = close <= close.rolling(divergence_window).min()
    wad_new_low = wad <= wad.rolling(divergence_window).min()
    bullish_divergence = price_new_low & (~wad_new_low)

    price_new_high = close >= close.rolling(divergence_window).max()
    wad_new_high = wad >= wad.rolling(divergence_window).max()
    bearish_divergence = price_new_high & (~wad_new_high)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    n = len(close)
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(bearish_divergence.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(bullish_divergence.iloc[i]):
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

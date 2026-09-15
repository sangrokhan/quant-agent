"""Strategy: HACO (Heikin-Ashi Candlestick Oscillator, Sylvain Vervoort) regime-flip.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Sylvain Vervoort's HACO indicator (S&C Dec 2008; Pine Script source disclosed
at https://www.tradingview.com/script/UyhY8FuQ-Vervoort-Heiken-Ashi-Candlestick-Oscillator/,
the base of the HACOLT regime filter at
https://www.tradingview.com/script/4zuhGaAU-Vervoort-Heiken-Ashi-LongTerm-Candlestick-Oscillator-LazyBear/)
computes a smoothed Heikin-Ashi close (haC), then applies a zero-lag TEMA
("zlTEMA" = TEMA of TEMA, lag-corrected) separately to haC and to hl2
(=(H+L)/2), each with its own up/down length parameter. A boolean "keep"
condition per direction (candle-color persistence, zero-lag-diff sign, and a
35%-body/prior-bar-overlap continuation rule) defines upTrend/dnTrend flags.
The oscillator (haco in {-1, 0, 1}) flips to +1 the bar dnTrend was true and
upTrend becomes newly true (regime reversal up), flips to -1 on the symmetric
down reversal, and otherwise holds its previous value. This is a smoothed
trend-regime detector distinct from any zero-lag-TEMA-crossover or plain
Heikin-Ashi color-flip strategy already tested in this repo (color-flip vs
ATR-trail was tested separately; this is Vervoort's own disclosed keep/trend
logic, not a naive close>open Heikin-Ashi rule).

Signal logic
------------
- Long (position=1) whenever the HACO oscillator value is +1.
- Flat (position=0) whenever HACO is -1 or 0 (this repo trades long-only;
  HACO's short-entry semantic is not used since generate_signals returns a
  {0,1} long/flat series per this repo's contract).
- Optional max_hold_days safety cap (avoid pathologically long holds if the
  regime never flips back, matching this repo's established convention).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def _tema(series: pd.Series, length: int) -> pd.Series:
    ema1 = _ema(series, length)
    ema2 = _ema(ema1, length)
    ema3 = _ema(ema2, length)
    return 3 * (ema1 - ema2) + ema3


def _zltema(series: pd.Series, length: int) -> pd.Series:
    tma1 = _tema(series, length)
    tma2 = _tema(tma1, length)
    diff = tma1 - tma2
    return tma1 + diff


def _compute_haco(df: pd.DataFrame, avg_up: int, avg_dn: int, keep_body_ratio: float) -> pd.Series:
    """Compute Vervoort's HACO oscillator series (values in {-1, 0, 1})."""
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]
    ohlc4 = (open_ + high + low + close) / 4.0
    hl2 = (high + low) / 2.0

    # haO recursive smoothed heikin-ashi open; haC derived from it.
    n = len(df)
    haO = np.empty(n)
    haO[:] = np.nan
    ohlc4_prev = ohlc4.shift(1)
    for i in range(n):
        prev_haO = haO[i - 1] if i > 0 and not np.isnan(haO[i - 1]) else 0.0
        prev_ohlc4 = ohlc4_prev.iloc[i]
        prev_ohlc4 = prev_ohlc4 if not pd.isna(prev_ohlc4) else ohlc4.iloc[i]
        haO[i] = (prev_ohlc4 + prev_haO) / 2.0
    haO = pd.Series(haO, index=df.index)
    haC = (ohlc4 + haO + pd.concat([high, haO], axis=1).max(axis=1) + pd.concat([low, haO], axis=1).min(axis=1)) / 4.0

    # Up branch
    upTMA1 = _zltema(haC, avg_up)
    upTMA2 = _zltema(upTMA1, avg_up)
    upDiff = upTMA1 - upTMA2
    upZlHa = upTMA1 + upDiff
    upTMA12 = _zltema(hl2, avg_up)
    upTMA22 = _zltema(upTMA12, avg_up)
    upDiff2 = upTMA12 - upTMA22
    upZlCl = upTMA12 + upDiff2
    upZlDiff = upZlCl - upZlHa

    upKeep1 = (haC >= haO) & (haC.shift(1) >= haO.shift(1))
    upKeep2 = upZlDiff >= 0
    upKeeping = upKeep1 | upKeep2
    upKeep3 = (close - open_).abs() < (high - low) * keep_body_ratio
    upKeep3 = upKeep3 & (high >= low.shift(1))
    upKeepAll_a = upKeeping
    upKeepAll_b = upKeeping.shift(1).fillna(False) & ((close >= open_) | (close >= close.shift(1)))
    upKeepAll = upKeepAll_a | upKeepAll_b
    upTrend = upKeepAll | (upKeepAll.shift(1).fillna(False) & upKeep3)

    # Down branch
    dnTMA1 = _zltema(haC, avg_dn)
    dnTMA2 = _zltema(dnTMA1, avg_dn)
    dnDiff = dnTMA1 - dnTMA2
    dnZlHa = dnTMA1 + dnDiff
    dnTMA12 = _zltema(hl2, avg_dn)
    dnTMA22 = _zltema(dnTMA12, avg_dn)
    dnDiff2 = dnTMA12 - dnTMA22
    dnZlCl = dnTMA12 + dnDiff2
    dnZlDiff = dnZlCl - dnZlHa

    dnKeep1 = (haC < haO) & (haC.shift(1) < haO.shift(1))
    dnKeep2 = dnZlDiff < 0
    dnKeep3 = (close - open_).abs() < (high - low) * keep_body_ratio
    dnKeep3 = dnKeep3 & (low <= high.shift(1))
    dnKeeping = dnKeep1 | dnKeep2
    dnKeepAll_a = dnKeeping
    dnKeepAll_b = dnKeeping.shift(1).fillna(False) & ((close < open_) | (close < close.shift(1)))
    dnKeepAll = dnKeepAll_a | dnKeepAll_b
    dnTrend = dnKeepAll | (dnKeepAll.shift(1).fillna(False) & dnKeep3)

    upTrend = upTrend.fillna(False)
    dnTrend = dnTrend.fillna(False)

    upw = (~dnTrend) & dnTrend.shift(1).fillna(False) & upTrend
    dnw = (~upTrend) & upTrend.shift(1).fillna(False) & dnTrend

    haco = np.zeros(n)
    for i in range(n):
        if upw.iloc[i]:
            haco[i] = 1.0
        elif dnw.iloc[i]:
            haco[i] = -1.0
        else:
            haco[i] = haco[i - 1] if i > 0 else 0.0
    return pd.Series(haco, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    avg_up: int = 34,
    avg_dn: int = 34,
    keep_body_ratio: float = 0.35,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series from the HACO oscillator."""
    df = _prep(price_df)
    haco = _compute_haco(df, avg_up=avg_up, avg_dn=avg_dn, keep_body_ratio=keep_body_ratio)
    position = (haco > 0).astype(int)

    # Enforce max_hold_days: force-flat if we've been long longer than the cap.
    if max_hold_days and max_hold_days > 0:
        pos = position.values.copy()
        hold = 0
        for i in range(len(pos)):
            if pos[i] == 1:
                hold += 1
                if hold > max_hold_days:
                    pos[i] = 0
                    hold = 0
            else:
                hold = 0
        position = pd.Series(pos, index=position.index)

    return position.reindex(df.index).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    avg_up: int = 34,
    avg_dn: int = 34,
    keep_body_ratio: float = 0.35,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df, avg_up=avg_up, avg_dn=avg_dn, keep_body_ratio=keep_body_ratio, max_hold_days=max_hold_days
    )
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

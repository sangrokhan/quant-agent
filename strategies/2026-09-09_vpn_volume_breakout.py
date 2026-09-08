"""Strategy: Volume Positive Negative (VPN) breakout, Markos Katsanos.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-066):
Per Financial Hacker's replication of Markos Katsanos' VPN indicator
(Stocks & Commodities April 2021, https://financial-hacker.com/petra-on-
programming-detecting-volume-breakouts/, browser_exec fallback --
web_search DDGS errored with a TLS connection error): each day is
classified as an "up day" if typical_price[t] > typical_price[t-1] +
0.1*ATR(period), or a "down day" if typical_price[t] < typical_price[t-1] -
0.1*ATR(period). VPN sums up-day volume (Vp) and down-day volume (Vn) over
a trailing period, and computes VPN = EMA(100*(Vp-Vn)/Vtotal, 3) -- a
volume-based breakout-strength oscillator distinct from every other volume
indicator already tested in this repo (OBV, MFI, CMF, KVO, PVO, Force
Index, Demand Index, VWMA/VW-MACD) via its ATR-threshold-gated up/down-day
volume classification rather than close-to-close sign, dollar-flow, or
typical-price-weighted-volume construction. Simplified single-asset
long-only adaptation of the source's own disclosed buy/sell rule: long
entry when VPN crosses above threshold (10) AND 50-day volume average is
rising vs its own trailing value AND RSI(5)<90 (avoid extreme overbought)
AND price above SMA(30) (uptrend confirmation); exit when VPN crosses below
its own 30-day SMA while price is more than 3*ATR(5) below the 5-day high
(momentum-stall + pullback exit, source's own rule), or a max_hold_days
time-stop (source's own 15-day default lifetime).

Signal logic
------------
- typical_price = (High+Low+Close)/3; dist = 0.1*ATR(period).
- up_day = typical_price > typical_price.shift(1) + dist
- down_day = typical_price < typical_price.shift(1) - dist
- Vp = rolling sum of volume on up days over `period`; Vn = rolling sum of
  volume on down days over `period`; Vtotal = rolling sum of all volume.
- VPN = EMA(100*(Vp-Vn)/Vtotal, 3)
- Entry (long): VPN crosses above threshold AND SMA(volume,50) >
  SMA(volume,50).shift(50) (rolling 50d vol average rising vs its own value
  50 bars ago, source's own comparison) AND RSI(close,5) < 90 AND
  close > SMA(close,30).
- Exit: VPN crosses below SMA(VPN,30) while close < (rolling 5-day high -
  3*ATR(5)), or a max_hold_days time-stop.
- Flat (no position) whenever not in an active long.

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5/6):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _vpn(df: pd.DataFrame, period: int = 30) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    dist = 0.1 * _atr(df, period)

    up_day = typical_price > (typical_price.shift(1) + dist)
    down_day = typical_price < (typical_price.shift(1) - dist)

    vp = (df["volume"].where(up_day, 0.0)).rolling(period).sum()
    vn = (df["volume"].where(down_day, 0.0)).rolling(period).sum()
    vtotal = df["volume"].rolling(period).sum()

    raw = 100 * (vp - vn) / vtotal.replace(0, np.nan)
    return raw.ewm(span=3, adjust=False).mean()


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 30,
    threshold: float = 10.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    vpn = _vpn(df, period=period)
    vpn_sma30 = vpn.rolling(30).mean()

    cross_over = (vpn > threshold) & (vpn.shift(1) <= threshold)
    vol_sma50 = volume.rolling(50).mean()
    vol_rising = vol_sma50 > vol_sma50.shift(50)
    rsi5 = _rsi(close, 5)
    close_above_sma30 = close > close.rolling(30).mean()

    entry = cross_over & vol_rising.fillna(False) & (rsi5 < 90) & close_above_sma30

    high5 = df["high"].rolling(5).max()
    atr5 = _atr(df, 5)
    stall_pullback = close < (high5 - 3 * atr5)
    vpn_cross_under_sma = (vpn < vpn_sma30) & (vpn.shift(1) >= vpn_sma30.shift(1))
    exit_cond = vpn_cross_under_sma & stall_pullback

    entry_arr = entry.to_numpy()
    exit_arr = exit_cond.to_numpy()
    pos_arr = np.zeros(len(df), dtype=int)

    in_pos = False
    entry_idx = -1
    for i in range(len(df)):
        if in_pos:
            held = i - entry_idx
            if exit_arr[i] or held >= max_hold_days:
                in_pos = False
            else:
                pos_arr[i] = 1
        if not in_pos and entry_arr[i]:
            in_pos = True
            entry_idx = i
            pos_arr[i] = 1

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 30,
    threshold: float = 10.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        period=period,
        threshold=threshold,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change()
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    return strat_returns

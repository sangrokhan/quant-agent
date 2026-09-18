"""Strategy: Price Zone Oscillator (PZO) trend-regime long-only entry/exit.

Hypothesis (source: TASC June 2011 Traders' Tips / "Entering The Price
Zone" by Walid Khalil and David Steckler, TradeStation EasyLanguage,
https://traders.com/documentation/feedbk_docs/2011/06/traderstips.html,
read via browser_exec fallback -- web_search's DDGS backend was
intermittently failing with TLS/connection errors this iteration):

The Price Zone Oscillator measures the EMA of sign(Close-Close[1])*Close
relative to the EMA of Close itself:

    R   = sign(Close - Close[-1]) * Close
    CP  = EMA(R, period)
    TC  = EMA(Close, period)
    PZO = 100 * CP / TC

PZO oscillates roughly in [-100, 100] and the source defines named zone
levels: ExtremeOverbot=60, Overbought=40, MidPlus=15, MidMinus=-5,
Oversold=-40, ExtremeOversold=-60. The source's own disclosed EasyLanguage
strategy switches behavior based on an ADX(14) trend-strength regime
(ADX > adx_trend_threshold means "trending"), and gates entries with an
EMA(60) price trend filter. This strategy implements the LONG-ONLY subset
of the source's disclosed logic in the ADX-trending branch (the more
economically motivated case -- trade continuation once a trend is
established), long-only per this repo's SAFETY.md:

Signal logic (trending regime, i.e. ADX(adx_length) > adx_trend_threshold)
------------------------------------------------------------------------
- Trend filter: close > EMA(ema_length) (source's own gating condition for
  entering longs in the trending regime).
- Entry (long), either of the source's two disclosed long triggers:
  1. PZO crosses above `oversold` (-40): a sharp momentum-recovery entry
     directly out of an oversold PZO reading.
  2. PZO crosses above 0 (recorded as a "confirmed" state), THEN later
     crosses above `mid_plus` (15): the source's two-stage "cross zero,
     then confirm strength" entry.
- Exit (source's own disclosed trending-regime sell logic):
  1. PZO had previously exceeded `extreme_overbot` (60) and has now turned
     down (this bar's PZO < prior bar's PZO) -- momentum peaking out after
     an extreme overbought reading, OR
  2. close falls below EMA(ema_length) while PZO < 0 (trend filter breaks
     while momentum has already turned negative).
- `max_hold_days` time-stop backstop (source gives no explicit time-stop;
  added per this repo's standard practice to avoid indefinite holds).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _pzo(close: pd.Series, period: int) -> pd.Series:
    r = np.sign(close.diff().fillna(0)) * close
    cp = r.ewm(span=period, adjust=False).mean()
    tc = close.ewm(span=period, adjust=False).mean()
    return 100.0 * cp / tc.replace(0, np.nan)


def _adx(df: pd.DataFrame, length: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prior_close = close.shift(1)
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = pd.concat([
        (high - low).abs(),
        (high - prior_close).abs(),
        (low - prior_close).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / length, adjust=False).mean()
    plus_di = 100.0 * pd.Series(plus_dm, index=df.index).ewm(alpha=1.0 / length, adjust=False).mean() / atr.replace(0, np.nan)
    minus_di = 100.0 * pd.Series(minus_dm, index=df.index).ewm(alpha=1.0 / length, adjust=False).mean() / atr.replace(0, np.nan)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1.0 / length, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    pzo_period: int = 14,
    adx_length: int = 14,
    adx_trend_threshold: float = 18.0,
    ema_length: int = 60,
    extreme_overbot: float = 60.0,
    oversold: float = -40.0,
    mid_plus: float = 15.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series (trending-regime long-only)."""
    df = _prep(price_df)
    close = df["close"]

    pzo = _pzo(close, pzo_period)
    adx = _adx(df, adx_length)
    ema = close.ewm(span=ema_length, adjust=False).mean()
    trending = adx > adx_trend_threshold
    above_ema = close > ema

    cross_over_oversold = (pzo > oversold) & (pzo.shift(1) <= oversold)
    cross_over_zero = (pzo > 0) & (pzo.shift(1) <= 0)
    cross_over_midplus = (pzo > mid_plus) & (pzo.shift(1) <= mid_plus)

    extreme_seen = (pzo.shift(1) > extreme_overbot)
    pzo_declining = pzo < pzo.shift(1)
    peak_out_exit = extreme_seen & pzo_declining
    ema_break_exit = (~above_ema) & (pzo < 0)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    zero_confirmed = False

    trending_vals = trending.fillna(False).to_numpy()
    above_ema_vals = above_ema.fillna(False).to_numpy()
    cross_oversold_vals = cross_over_oversold.fillna(False).to_numpy()
    cross_zero_vals = cross_over_zero.fillna(False).to_numpy()
    cross_midplus_vals = cross_over_midplus.fillna(False).to_numpy()
    peak_out_vals = peak_out_exit.fillna(False).to_numpy()
    ema_break_vals = ema_break_exit.fillna(False).to_numpy()

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if peak_out_vals[i] or ema_break_vals[i] or held >= max_hold_days:
                in_position = False
                zero_confirmed = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if trending_vals[i] and above_ema_vals[i]:
                if cross_zero_vals[i]:
                    zero_confirmed = True
                entry_signal = cross_oversold_vals[i] or (zero_confirmed and cross_midplus_vals[i])
                if entry_signal:
                    in_position = True
                    entry_idx = i
                    zero_confirmed = False
                    position.iloc[i] = 1
                else:
                    position.iloc[i] = 0
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

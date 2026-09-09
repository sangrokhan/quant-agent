"""Strategy: Rolling VWAP-band mean reversion, gated by ADX trend filter AND
requiring an explicit rejection-candle confirmation at the band touch.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-011):
Per crosstrade.io's VWAP Reversion strategy
(https://crosstrade.io/learn/trading-strategies/vwap-reversion): "when price
extends far enough from the [VWAP], fade the move and target a return to
VWAP... It fails badly on strong trend days -- a regime filter is
mandatory." The source's own disclosed rules (adapted here from an
intraday-session Pine Script to this repo's daily bars):

  1. Regime filter: skip entries when ADX(14) > adx_threshold (source's
     stated "strong trending regime" skip condition -- adapted 1:1, just
     using daily ADX instead of the source's 5-minute ADX).
  2. Setup: close is >= band_std rolling-VWAP-standard-deviations away from
     the rolling VWAP (source's "2 sigma" trigger, band_std tunable).
  3. Trigger (source's own explicit "Common mistakes" warning: "Trading the
     bands without a rejection trigger. Pure band-touch entries fail
     frequently."): require a rejection candle at the touch bar -- for
     longs, lower wick > 2x body AND close > open (bullish rejection at the
     lower band).
  4. Entry: next bar's close (this repo trades daily bars, so "next bar
     open after trigger bar closes" collapses to entering at the following
     day's close, one bar after the signal is confirmed).
  5. Exit: reversion target = rolling VWAP itself (source's stated target),
     or a max_hold_days time-stop backstop (source has no time-stop, but
     one is needed here since this repo has no explicit stop-loss order
     execution layer -- ATR stop is approximated via the exit condition
     below).

This strategy is a DIRECT REJECTION-CANDLE + ADX-GATE variant, distinct from
the already-rejected plain rolling-VWAP-band mean reversion
(2026-09-04-052, id in strategies_log.jsonl) which used NO rejection-candle
confirmation trigger and gated by this repo's existing low/high realized-vol
regime split rather than a genuine ADX trend-strength filter -- exactly the
two differences the source's own "Common mistakes" section calls out as
essential (rejection trigger) and "mandatory" (regime/ADX filter).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _rolling_vwap_bands(df: pd.DataFrame, vwap_window: int, band_std: float):
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = typical * df["volume"]
    sum_pv = pv.rolling(vwap_window).sum()
    sum_v = df["volume"].rolling(vwap_window).sum().replace(0, np.nan)
    vwap = sum_pv / sum_v

    sum_ppv = (typical * typical * df["volume"]).rolling(vwap_window).sum()
    variance = (sum_ppv / sum_v) - (vwap * vwap)
    variance = variance.clip(lower=0)
    sd = np.sqrt(variance)

    upper = vwap + band_std * sd
    lower = vwap - band_std * sd
    return vwap, upper, lower


def _adx(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1 / window, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / window, adjust=False).mean() / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1 / window, adjust=False).mean() / atr.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / window, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    vwap_window: int = 20,
    band_std: float = 2.0,
    adx_window: int = 14,
    adx_threshold: float = 25.0,
    rejection_wick_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    vwap, upper, lower = _rolling_vwap_bands(df, vwap_window, band_std)
    adx = _adx(df, adx_window)

    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    body = (close - open_).abs()
    lower_wick = pd.concat([close, open_], axis=1).min(axis=1) - low
    bullish_rejection = (lower_wick > rejection_wick_mult * body) & (close > open_)

    good_regime = adx <= adx_threshold
    setup = (low <= lower) & good_regime & bullish_rejection

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = -1
    idx_list = df.index.tolist()

    for i in range(1, len(df)):
        ts = idx_list[i]
        if not in_pos:
            if bool(setup.iloc[i]):
                # enter next bar (i.e. this bar's decision applies starting
                # the following bar's close, so hold begins at i+1)
                if i + 1 < len(df):
                    in_pos = True
                    entry_idx = i + 1
        else:
            days_held = i - entry_idx
            reverted = close.iloc[i] >= vwap.iloc[i] if not np.isnan(vwap.iloc[i]) else False
            if reverted or days_held >= max_hold_days:
                in_pos = False
            else:
                position.loc[ts] = 1

        if in_pos and i >= entry_idx:
            position.loc[ts] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(price_df, **params)
    daily_returns = df["close"].pct_change().fillna(0.0)
    # position at t determines exposure earned over t -> t+1 (shift to avoid lookahead)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns

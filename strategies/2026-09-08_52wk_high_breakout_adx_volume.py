"""Strategy: 52-week-high breakout with volume + ADX trend-strength
confirmation, EMA trend-break exit + trailing-stop.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
per https://swingfolio.com/blog/52-week-high-breakout-trading-strategy,
a stock closing above its highest close of the last ~252 trading days
("52-week high") clears overhead resistance from trapped sellers, and
tends to keep rising ("new highs make new highs"). Source's own entry
checklist requires: (1) daily close above the 252-day rolling high,
(2) volume >= 1.5x the 50-day average volume (institutional
participation confirmation), (3) ADX(14) > 20 and rising (confirms a
real trend, not sideways drift). Exit: close below the 20-day EMA
(trend-break) OR a percentage trailing stop from the post-entry peak
(source uses 7%, exposed here as a tunable param).

Signal logic
------------
- rolling_high(lookback) = highest close over the last `lookback` bars
  (default 252, ~52 weeks of trading days), EXCLUDING today's bar (shift
  by 1 to avoid lookahead/self-reference).
- Entry (long): close > rolling_high AND volume >= vol_mult * SMA(volume,
  vol_window) AND ADX(adx_period) > adx_threshold AND ADX is rising
  (ADX_t > ADX_{t-1}).
- Exit: close < EMA(ema_period) (trend-break), OR close < (highest close
  since entry) * (1 - trail_pct) (percentage trailing stop), OR
  max_hold_days time-stop (backstop; source's own rules have no explicit
  time-stop but this repo's convention adds one to avoid indefinite
  holds).
- Flat otherwise.

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


def _adx(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    up_move = high - prev_high
    down_move = prev_low - low

    plus_dm = ((up_move > down_move) & (up_move > 0)).astype(float) * up_move.clip(lower=0)
    minus_dm = ((down_move > up_move) & (down_move > 0)).astype(float) * down_move.clip(lower=0)

    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / period, adjust=False).mean() / atr
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / period, adjust=False).mean() / atr

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.ewm(alpha=1.0 / period, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 252,
    vol_window: int = 50,
    vol_mult: float = 1.5,
    adx_period: int = 14,
    adx_threshold: float = 20.0,
    ema_period: int = 20,
    trail_pct: float = 0.07,
    max_hold_days: int = 60,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(0.0, index=df.index)

    rolling_high = close.shift(1).rolling(lookback).max()
    vol_sma = volume.rolling(vol_window).mean()
    adx = _adx(df, adx_period)
    ema = close.ewm(span=ema_period, adjust=False).mean()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_days = 0
    highest_close_since_entry = None

    for i in range(len(df.index)):
        c = close.iloc[i]
        rh = rolling_high.iloc[i]
        v = volume.iloc[i]
        vs = vol_sma.iloc[i]
        a = adx.iloc[i]
        a_prev = adx.iloc[i - 1] if i > 0 else float("nan")
        e = ema.iloc[i]

        if in_position:
            hold_days += 1
            if highest_close_since_entry is None or c > highest_close_since_entry:
                highest_close_since_entry = c
            trend_break = (not pd.isna(e)) and c < e
            trailing_stop_hit = (
                highest_close_since_entry is not None
                and c < highest_close_since_entry * (1 - trail_pct)
            )
            if trend_break or trailing_stop_hit or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                highest_close_since_entry = None
            else:
                position.iloc[i] = 1
        else:
            breakout = (not pd.isna(rh)) and c > rh
            vol_confirmed = (not pd.isna(vs)) and vs > 0 and v >= vol_mult * vs
            adx_confirmed = (
                not pd.isna(a) and not pd.isna(a_prev) and a > adx_threshold and a > a_prev
            )
            if breakout and vol_confirmed and adx_confirmed:
                in_position = True
                hold_days = 1
                highest_close_since_entry = c
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    lookback: int = 252,
    vol_window: int = 50,
    vol_mult: float = 1.5,
    adx_period: int = 14,
    adx_threshold: float = 20.0,
    ema_period: int = 20,
    trail_pct: float = 0.07,
    max_hold_days: int = 60,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        lookback=lookback,
        vol_window=vol_window,
        vol_mult=vol_mult,
        adx_period=adx_period,
        adx_threshold=adx_threshold,
        ema_period=ema_period,
        trail_pct=trail_pct,
        max_hold_days=max_hold_days,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns

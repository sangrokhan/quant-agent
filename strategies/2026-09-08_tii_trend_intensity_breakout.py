"""Strategy: Trend Intensity Index (TII) breakout with SMA trend filter and
ATR trailing stop.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
per https://pinescriptforge.com/strategy/trend-intensity-index, the Trend
Intensity Index (TII) counts the number of days price closed above (vs
below) a moving average over a lookback period, expressed as a 0-100
percentage -- directional and faster-responding than ADX (which is
non-directional trend STRENGTH only). Readings above 80 indicate strong
uptrends, below 20 strong downtrends, 50 = no trend. Source's own strategy:
TII(30)/SMA(50)/ATR(14); long entry when TII crosses above 80 AND price is
above the 50-SMA; exit when TII crosses back below 50 (against position)
or a 1.5x ATR trailing stop is hit. Source's own 64-symbol futures backtest
showed decisively mixed results (profit factor 0.18-2.5 depending on
instrument) -- this repo tests it on QQQ/SPY/BTC/ETH specifically.

Signal logic
------------
- TII(tii_period) = 100 * count(close_t > SMA(sma_period)_t for the last
  tii_period bars) / tii_period.
- Entry (long): TII crosses from <=80 to >80 AND close > SMA(sma_period).
- Exit: TII crosses from >=50 to <50 (trend intensity collapse), OR close
  drops below (highest close since entry) - atr_mult * ATR(atr_period)
  (a ratcheting/trailing ATR stop), OR max_hold_days time-stop.
- Flat otherwise.

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


def _tii(close: pd.Series, sma_period: int, tii_period: int) -> pd.Series:
    sma = close.rolling(sma_period).mean()
    above = (close > sma).astype(float)
    return 100.0 * above.rolling(tii_period).sum() / tii_period


def _atr(df: pd.DataFrame, atr_period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(atr_period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    tii_period: int = 30,
    sma_period: int = 50,
    atr_period: int = 14,
    entry_tii: float = 80.0,
    exit_tii: float = 50.0,
    atr_mult: float = 1.5,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(sma_period).mean()
    tii = _tii(close, sma_period, tii_period)
    atr = _atr(df, atr_period)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_days = 0
    highest_close_since_entry = None

    for i in range(len(df.index)):
        t = tii.iloc[i]
        t_prev = tii.iloc[i - 1] if i > 0 else float("nan")
        c = close.iloc[i]
        s = sma.iloc[i]
        a = atr.iloc[i]

        if in_position:
            hold_days += 1
            if highest_close_since_entry is None or c > highest_close_since_entry:
                highest_close_since_entry = c
            trailing_stop_hit = (
                not pd.isna(a) and highest_close_since_entry is not None
                and c < (highest_close_since_entry - atr_mult * a)
            )
            tii_exit = (not pd.isna(t)) and (not pd.isna(t_prev)) and t_prev >= exit_tii and t < exit_tii
            if tii_exit or trailing_stop_hit or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                highest_close_since_entry = None
            else:
                position.iloc[i] = 1
        else:
            crossed_up = (not pd.isna(t)) and (not pd.isna(t_prev)) and t_prev <= entry_tii and t > entry_tii
            trend_ok = (not pd.isna(s)) and c > s
            if crossed_up and trend_ok:
                in_position = True
                hold_days = 1
                highest_close_since_entry = c
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    tii_period: int = 30,
    sma_period: int = 50,
    atr_period: int = 14,
    entry_tii: float = 80.0,
    exit_tii: float = 50.0,
    atr_mult: float = 1.5,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        tii_period=tii_period,
        sma_period=sma_period,
        atr_period=atr_period,
        entry_tii=entry_tii,
        exit_tii=exit_tii,
        atr_mult=atr_mult,
        max_hold_days=max_hold_days,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns

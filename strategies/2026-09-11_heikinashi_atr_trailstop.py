"""Strategy: Heikin-Ashi trend-following with an ATR trailing-stop exit
(instead of the eager single-candle color-flip exit).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-101):
This repo's prior Heikin-Ashi trend-following attempt (2026-09-04-045:
long when price > EMA(trend_window) AND N consecutive bullish HA candles,
exit on the FIRST bearish HA candle) was rejected -- not decisively, but
because the "single-candle flip" exit was too eager, cutting winners on
shallow pullbacks (133 trades on QQQ alone over 7.7yr at the grid-optimal
params, a high turnover rate for a nominally trend-following system per
that entry's own notes). Per a Google AI-overview synthesis of
PyQuantLab/Medium/Kridtapon P./Tradeworks Heikin-Ashi guides (visited this
iteration), the source's own fuller compound rule uses a trailing stop
(percentage or ATR-multiple) INSTEAD OF a bare color-flip, specifically to
avoid exiting trend continuations on a single noisy reversal candle.

This strategy directly re-tests the same underlying HA-momentum signal
but swaps the exit mechanism for an ATR(atr_window) trailing stop
(running favorable HA-close high minus atr_mult * ATR), addressing the
prior rejection's own documented root cause rather than abandoning the
indicator family.

Signal logic
------------
- Compute Heikin-Ashi OHLC from the raw OHLC (standard HA formulas).
- Entry (long): close (raw) > EMA(trend_window) AND the last
  `consecutive_count` HA candles are all bullish (HA_close > HA_open).
- Exit: raw close falls below a trailing stop line = running max of raw
  close since entry, minus atr_mult * ATR(atr_window) (computed on raw
  OHLC) -- OR the EMA trend filter breaks (raw close < EMA(trend_window)),
  whichever comes first. No fixed max-hold (trend-following: let winners
  run, the ATR trail is the only brake).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} long/flat)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    ha_close = (o + h + l + c) / 4.0
    ha_open = pd.Series(index=df.index, dtype=float)
    ha_open.iloc[0] = (o.iloc[0] + c.iloc[0]) / 2.0
    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2.0
    return pd.DataFrame({"ha_open": ha_open, "ha_close": ha_close})


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat(
        [(h - l).abs(), (h - prev_c).abs(), (l - prev_c).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    consecutive_count: int = 2,
    atr_window: int = 14,
    atr_mult: float = 3.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema = close.ewm(span=trend_window, adjust=False).mean()
    ha = _heikin_ashi(df)
    bullish = ha["ha_close"] > ha["ha_open"]
    consec_bull = bullish.rolling(consecutive_count).sum() == consecutive_count

    atr = _atr(df, atr_window)

    entry = (close > ema).fillna(False) & consec_bull.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    trail_high = None

    for i in range(len(close)):
        px = close.iloc[i]
        if in_position:
            trail_high = px if trail_high is None else max(trail_high, px)
            a = atr.iloc[i]
            stop_line = trail_high - atr_mult * a if pd.notna(a) else None
            trend_broken = pd.notna(ema.iloc[i]) and px < ema.iloc[i]
            stopped_out = stop_line is not None and px < stop_line
            if trend_broken or stopped_out:
                in_position = False
                trail_high = None
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                trail_high = px
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

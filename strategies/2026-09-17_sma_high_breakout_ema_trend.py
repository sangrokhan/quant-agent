"""Strategy: Swing Trading With Three Indicators (Donald Pendergast, TASC
December 2013), long-only adaptation. Read this iteration via browser_exec
at https://traders.com/documentation/feedbk_docs/2013/12/traderstips.html
(EasyLanguage code disclosed directly in the article's TradeStation Traders'
Tips code section, credited to Doug McCrary/TradeStation Securities).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-115):
A breakout of a SHORT SMA-of-HIGHS (not a raw rolling-max Donchian band)
plus a small fixed-tick buffer, gated by the prior bar's close being above a
long EMA (trend filter), marks a higher-quality long entry than an
unconditional SMA-of-high breakout, because the EMA filter excludes
breakouts that occur against the prevailing trend. Exit when price falls
back below the SMA-of-lows. This differs from the repo's existing Donchian
breakout entries (e.g. donchian_breakout_trend.py, donchian_turtle_breakout.py)
because those use raw ROLLING MAX/MIN of high/low (Donchian channels), while
this construction uses a rolling AVERAGE (SMA) of high/low as the breakout
reference level -- a materially smoother/tighter band that breaks more often,
with the EMA trend filter and a small tick-buffer specifically added by the
source to reduce whipsaw.

Exact formula (from TASC Dec 2013 TradeStation EasyLanguage, as read this
iteration; percentage buffer used here in place of "ticks" since prices are
adjusted-close daily bars not tick-denominated):
    SMAHighValue = SMA(High, sma_length)
    SMALowValue  = SMA(Low, sma_length)
    EMAValue     = EMA(Close, ema_length)
    Long entry:  Close[t-1] > EMAValue[t-1]
                 AND High[t] crosses over (SMAHighValue[t] * (1 + breakout_buffer_pct))
    Long exit:   Low[t] < SMALowValue[t]

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    sma_length: int = 5,
    ema_length: int = 50,
    breakout_buffer_pct: float = 0.001,
) -> pd.Series:
    """Return a {0,1} long/flat position series (long-only adaptation of
    Pendergast's swing trading system)."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    sma_high = high.rolling(sma_length).mean()
    sma_low = low.rolling(sma_length).mean()
    ema = close.ewm(span=ema_length, adjust=False).mean()

    breakout_level = sma_high * (1.0 + breakout_buffer_pct)
    trend_ok = close.shift(1) > ema.shift(1)
    breakout_cross = (high.shift(1) <= breakout_level.shift(1)) & (high > breakout_level)

    entry = trend_ok & breakout_cross.fillna(False)
    exit_cond = low < sma_low

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if bool(exit_cond.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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

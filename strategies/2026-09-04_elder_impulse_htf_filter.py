"""Strategy: Alexander Elder's Impulse System, gated by his own recommended
higher-timeframe (5x) trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-125):
Elder's Impulse System (Come Into My Trading Room, 2002) color-codes each
bar green/red/blue based on the joint slope of a 13-period EMA (trend) and
the standard MACD Histogram (momentum): green = both rising (bulls in
control of trend AND momentum). Per quantifiedstrategies.com, Elder himself
advises trading Impulse signals ONLY in the direction of a higher-timeframe
trend ~5x the trading timeframe (e.g. weekly 13-EMA when trading daily bars,
approximated here as a 65-period (13x5) EMA computed directly on daily
bars). This repo already tested the plain Impulse System without the HTF
filter (2026-09-04-064, rejected decisively on QQQ, near-miss on SPY) --
this iteration specifically adds the HTF filter Elder himself calls
essential, addressing that prior rejection rather than re-testing the same
bare rule.

Signal logic
------------
- fast_ema = EMA(close, 13); macd_hist = MACD(12,26,9) histogram.
- Bar is "green" (bullish impulse) when fast_ema is rising (fast_ema >
  fast_ema.shift(1)) AND macd_hist is rising (macd_hist > macd_hist.shift(1)).
- htf_trend_up = EMA(close, htf_window) is rising (approximates a
  higher-timeframe uptrend filter, htf_window default 65 = 13*5).
- Entry (long): bar turns green (green today, not green yesterday) AND
  htf_trend_up.
- Exit: bar stops being green (color changes away from green), OR
  htf_trend_up turns false, OR max_hold_days elapses.
- Long-only, flat otherwise.

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


def _macd_hist(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 13,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    htf_window: int = 65,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_ema = close.ewm(span=ema_window, adjust=False).mean()
    hist = _macd_hist(close, macd_fast, macd_slow, macd_signal)
    htf_ema = close.ewm(span=htf_window, adjust=False).mean()

    ema_rising = fast_ema > fast_ema.shift(1)
    hist_rising = hist > hist.shift(1)
    is_green = ema_rising & hist_rising

    htf_trend_up = htf_ema > htf_ema.shift(1)

    turned_green = is_green & (~is_green.shift(1).fillna(False))

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            green_i = bool(is_green.iloc[i]) if pd.notna(is_green.iloc[i]) else False
            htf_i = bool(htf_trend_up.iloc[i]) if pd.notna(htf_trend_up.iloc[i]) else False
            if (not green_i) or (not htf_i) or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entry_i = bool(turned_green.iloc[i]) if pd.notna(turned_green.iloc[i]) else False
            htf_i = bool(htf_trend_up.iloc[i]) if pd.notna(htf_trend_up.iloc[i]) else False
            if entry_i and htf_i:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    ema_window: int = 13,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    htf_window: int = 65,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        ema_window=ema_window,
        macd_fast=macd_fast,
        macd_slow=macd_slow,
        macd_signal=macd_signal,
        htf_window=htf_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

"""Strategy: Long-only Donchian channel breakout, gated by a 200-day trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-008):
Source: https://secuora.net/strategy/donchian-breakout — a 2026 backtest of
the classic Turtle-style 20-bar Donchian channel breakout (long AND short,
bidirectional, hourly, no trend filter) on BTC/ETH found it net-losing on
both symbols over a 12-month window (profit factor 0.76-0.97, MDD 27-52%,
win rate ~33%) -- explicitly attributed by the source to "a breakout system
is only as good as the trends the instrument happens to print": taking every
breakout in both directions means eating whipsaws in choppy/ranging periods.

This strategy tests a deliberately narrower, long-only daily variant that
directly addresses that failure mode: only take Donchian upside breakouts
that occur ABOVE the 200-day SMA (established uptrend), and skip all short
signals entirely (also required by SAFETY.md / prior loop convention of
long-only strategies). The hypothesis is that filtering out breakouts against
the primary trend removes most of the whipsaw/false-breakout trades that hurt
the unconditional bidirectional version, while keeping the core "ride
established trends" edge -- distinct from 2026-09-03-004 (SMA200 + absolute
*momentum-return* filter) because entries here are triggered by a *price
channel breakout level* (N-day high), not by a trailing return threshold,
and exits are a symmetric N/2-day low breakout (trailing channel stop) rather
than a fixed holding period or vol-regime flip.

Signal logic
------------
- Trend filter: close > 200-day SMA (long regime only).
- Entry (long): close > rolling max of the prior `entry_window` days' highs
  (Donchian upper channel, computed on `high` excluding the current bar) AND
  in the long regime.
- Exit: close < rolling min of the prior `exit_window` days' lows (Donchian
  lower channel / trailing stop, excluding current bar) OR the trend filter
  flips (close < 200-day SMA).
- Flat otherwise; long-only (no shorts), per SAFETY.md.

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


def generate_signals(
    price_df: pd.DataFrame,
    entry_window: int = 20,
    exit_window: int = 10,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()
    uptrend = close > trend_sma

    # Exclude current bar from the channel calc (shift by 1) to avoid using
    # today's own high/low to trigger today's own entry/exit signal.
    upper_channel = high.rolling(entry_window).max().shift(1)
    lower_channel = low.rolling(exit_window).min().shift(1)

    entry = (close > upper_channel) & uptrend.fillna(False)
    exit_channel = close < lower_channel
    exit_trend_flip = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_channel.iloc[i]) or bool(exit_trend_flip.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
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
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

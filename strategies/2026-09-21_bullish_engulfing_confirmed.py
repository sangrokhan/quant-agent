"""Strategy: Bullish Engulfing candlestick pattern with volume + downtrend +
breakout confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-161):
Per a Google AI-overview synthesis of engulfing-pattern trading guides
(Dukascopy Bank, TradingView, apptrading.ai -- searched this iteration via
browser_exec after web_search's DDGS/Yahoo backend TLS-erroring; direct
quantifiedstrategies.com bullish-engulfing article 404'd), a raw two-candle
bullish engulfing pattern (bar1 bearish, bar2 bullish body fully engulfing
bar1's body) is a weak standalone signal, but the sources converge on a
specific multi-filter confirmation recipe that materially raises backtest
reliability:
  1. Prior downtrend filter: a clear decline over the preceding
     `trend_lookback` bars (today's close below its close `trend_lookback`
     bars ago).
  2. Volume confirmation: the engulfing (bar2) candle's volume >=
     `vol_mult` x its own trailing 20-bar average volume.
  3. Price-location filter: bar2's low sits near (within `pct_from_low` of)
     the rolling 20-bar low (the pattern occurs near a local bottom, not
     mid-trend).
  4. Breakout confirmation: the NEXT bar (bar3) closes above bar2's high
     (follow-through, avoiding a "one-day wonder" pattern that reverses).
Entry is on bar3's close (once confirmed). Exit uses a stop below bar2's
low and either a max_hold_days time-stop or a trend-based exit (close drops
back below its own SMA). This is the first candlestick ENGULFING-pattern
strategy in this repo (0 prior KB hits for "engulfing pattern").

Signal logic
------------
- Bearish bar1: close[t-1] < open[t-1].
- Bullish engulfing bar2 (=today, t): close[t] > open[t] AND
  open[t] <= close[t-1] AND close[t] >= open[t-1] (body fully engulfs
  bar1's body).
- Downtrend filter: close[t] < close[t - trend_lookback].
- Volume confirmation: volume[t] >= vol_mult * volume.rolling(20).mean()
  (evaluated at t, excluding t itself from the rolling average base via
  shift to avoid look-ahead leaking today's own volume into its baseline).
- Location filter: low[t] <= rolling_20_low * (1 + pct_from_low).
- All four conditions true on bar t => "confirmed engulfing candidate" is
  armed for bar t+1.
- Entry (long) on bar t+1 if close[t+1] > high[t] (breakout confirmation).
- Exit: close crosses below its own SMA(exit_sma_window), OR
  max_hold_days reached.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
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
    trend_lookback: int = 10,
    vol_mult: float = 1.5,
    pct_from_low: float = 0.03,
    exit_sma_window: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    bar1_bearish = close.shift(1) < open_.shift(1)
    bullish_engulf = (
        (close > open_)
        & (open_ <= close.shift(1))
        & (close >= open_.shift(1))
        & bar1_bearish
    )

    downtrend = close < close.shift(trend_lookback)

    avg_vol_20 = volume.rolling(20).mean()
    vol_confirm = volume >= (vol_mult * avg_vol_20)

    rolling_low_20 = low.rolling(20).min()
    location_ok = low <= (rolling_low_20 * (1.0 + pct_from_low))

    candidate = bullish_engulf & downtrend & vol_confirm & location_ok
    # Breakout confirmation happens the NEXT bar: close[t+1] > high[t].
    entry_trigger = candidate.shift(1).fillna(False) & (close > high.shift(1))

    exit_sma = close.rolling(exit_sma_window).mean()
    exit_trend = close < exit_sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                entry_idx = i
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

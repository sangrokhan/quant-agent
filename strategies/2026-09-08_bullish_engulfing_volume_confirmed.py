"""Strategy: Bullish Engulfing candlestick pattern, gated by a VOLUME
confirmation filter (institutional-participation proxy), within a
long-term uptrend.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-024):
Per tradingstrategyguides.com's engulfing-candle guide
(https://tradingstrategyguides.com/complete-guide-to-the-bullish-and-bearish-engulfing-candle-strategy/),
a plain bullish-engulfing pattern is unreliable on its own, but the source
explicitly states "Volume expansion on the engulfing candle significantly
increases the probability of a genuine trend reversal" and specifies a
concrete rule: "the volume on the second candle must be noticeably higher
than the volume of the preceding 3-5 candles". This repo already tested a
plain Bullish Engulfing + SMA200 trend filter (id=2026-09-04-102, rejected,
"likely needs a confirming ... extreme-reading input") -- this iteration
adds exactly the volume-expansion confirmation gate the source itself
recommends, which is the concrete, testable difference from -102.

Signal logic
------------
- Trend filter: close > SMA(trend_window) (default 200).
- Pattern: Day1 bearish real body (close < open); Day2 bullish real body
  (close > open) whose body fully engulfs Day1's body
  (Day2 open <= Day1 close AND Day2 close > Day1 open).
- Volume confirmation gate: Day2 volume >= volume_ratio * mean(volume over
  the preceding vol_lookback_days, e.g. 3-5 per source) -- this is the new
  ingredient vs. -102.
- Entry: long at Day2 close when pattern + trend filter + volume gate all
  hold.
- Exit: close crosses back below the 5-day SMA (mean-reversion target,
  matches -102's exit for apples-to-apples comparison), OR the trend filter
  breaks (close < SMA(trend_window)), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py /
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    trend_window: int = 200,
    exit_sma_window: int = 5,
    vol_lookback_days: int = 4,
    volume_ratio: float = 1.5,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    trend_sma = close.rolling(trend_window).mean()
    exit_sma = close.rolling(exit_sma_window).mean()
    uptrend = close > trend_sma

    day1_bearish = close.shift(1) < open_.shift(1)
    day2_bullish = close > open_
    engulf = (open_ <= close.shift(1)) & (close > open_.shift(1))

    avg_vol_prior = volume.shift(1).rolling(vol_lookback_days).mean()
    vol_confirmed = volume >= (volume_ratio * avg_vol_prior)

    entry_signal = day1_bearish & day2_bullish & engulf & uptrend & vol_confirmed
    entry_signal = entry_signal.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = None
    idx_list = close.index

    for i in range(len(idx_list)):
        ts = idx_list[i]
        if not in_position:
            if bool(entry_signal.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
        else:
            held_days = i - entry_idx
            trend_broken = bool(close.iloc[i] < trend_sma.iloc[i]) if pd.notna(trend_sma.iloc[i]) else False
            mean_reverted = bool(close.iloc[i] < exit_sma.iloc[i]) if pd.notna(exit_sma.iloc[i]) else False
            if mean_reverted or trend_broken or held_days >= max_hold_days:
                position.iloc[i] = 0
                in_position = False
                entry_idx = None
            else:
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    exit_sma_window: int = 5,
    vol_lookback_days: int = 4,
    volume_ratio: float = 1.5,
    max_hold_days: int = 10,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs applied)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        trend_window=trend_window,
        exit_sma_window=exit_sma_window,
        vol_lookback_days=vol_lookback_days,
        volume_ratio=volume_ratio,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns

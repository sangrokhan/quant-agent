"""Strategy: NR7 (Narrow Range 7) trend-continuation breakout with EMA filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-081):
Toby Crabel's NR7 pattern (Crabel, "Day Trading with Short Term Price
Patterns and Opening Range Breakout") identifies a bar whose high-low range
is the narrowest of the last N=7 bars -- a range-contraction ("calm before
the storm") that historically precedes a range-expansion move. Per
tradingsetupsreview.com's concrete trading rule (adapted here from
intraday 3-minute bars to this repo's daily bars): when the N bars leading
up to and including the NR7 bar are ALL above a 20-period EMA (established
uptrend), a breakout above the NR7 bar's high is a low-risk long entry
joining the trend, since the pattern indicates trend continuation
(momentum pause + trend confirmation) rather than reversal. This is
distinct from every previously-tested breakout strategy in this repo
(Donchian/Turtle -008/-054, BB-squeeze -??? etc.) because the breakout
trigger level here is defined by a *volatility-contraction* bar
specifically (narrowest range of the lookback window), not a rolling
high/low channel or a fixed-width band.

Signal logic
------------
- EMA(ema_window) is the trend filter.
- For each bar, look at the trailing `nr_window` bars (inclusive of the
  current bar): if the current bar's (high - low) range is the smallest
  of that window, it's an NR (narrow-range) bar.
- Trend confirmation: ALL of the trailing `nr_window` bars' closes must be
  above the EMA (established uptrend, per the source's "all above 20 EMA"
  rule).
- Entry (long): the day AFTER a confirmed NR bar (in an uptrend), price
  closes above the NR bar's high (breakout).
- Exit: after a fixed `max_hold_days` holding period, OR if close drops
  back below the EMA (trend filter invalidated), whichever comes first.
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


def generate_signals(
    price_df: pd.DataFrame,
    nr_window: int = 7,
    ema_window: int = 20,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    bar_range = high - low
    is_narrowest = bar_range == bar_range.rolling(nr_window).min()

    ema = close.ewm(span=ema_window, adjust=False).mean()
    above_ema = close > ema
    # all trailing nr_window bars' closes above EMA
    trend_confirmed = above_ema.rolling(nr_window).apply(lambda x: float(x.all()), raw=True).astype(bool)

    nr_confirmed = (is_narrowest & trend_confirmed).fillna(False)
    nr_bar_high = high.where(nr_confirmed)
    # breakout trigger level: the most recent confirmed NR bar's high, carried forward
    trigger_level = nr_bar_high.ffill()
    # only valid while we haven't already broken out beyond it and while within a
    # short lookahead window (avoid stale/ancient trigger levels firing much later)
    bars_since_nr = (~nr_confirmed).groupby((nr_confirmed).cumsum()).cumcount()
    # breakout entry: close breaks above trigger level, within 5 bars of the NR bar,
    # and we are still in an uptrend (close > EMA)
    breakout = (close > trigger_level) & (bars_since_nr <= 5) & (close > ema) & trigger_level.notna()

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    entered_idx = -1
    for i in range(n):
        if in_pos:
            hold_count += 1
            still_trend = close.iloc[i] > ema.iloc[i]
            if hold_count >= max_hold_days or not still_trend:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(breakout.iloc[i]):
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    nr_window: int = 7,
    ema_window: int = 20,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, nr_window=nr_window, ema_window=ema_window, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    # position taken at prior day's signal (avoid lookahead: shift by 1)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

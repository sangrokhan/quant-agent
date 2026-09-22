"""Strategy: N-day-high (Donchian) breakout, gated by Bulkowski's
Moving-Average-Position pre-breakout filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: Bulkowski's Moving Average Study (https://thepatternsite.com/MovingAvgs.html,
read via browser_exec this iteration; 21,696 sample chart-pattern trades,
April 1989-January 2009). Source's own disclosed, counter-intuitive
("contrarian") finding: for an UPWARD breakout in ANY market condition, the
average post-breakout move is LARGER and the failure rate LOWER when the
close the day BEFORE the breakout is BELOW (not above) the 9-day SMA
(26.2%/28.4% avg move & 29.7-32.7% fail rate vs. 26.5%/32.2% unconditional
benchmark). The source's own interpretation: price dipping under the very
short 9-day average right before an upside breakout reflects a brief
pullback/shakeout that (per the source's large sample) tends to precede a
stronger continuation than a breakout that had already been trading above
its short MA.

Adapted to a purely mechanical, no-chart-pattern-classification construction
(this repo's daily-OHLCV-only data cannot detect Bulkowski's 36 named chart
pattern types): define "breakout" as a new N-day-high (Donchian channel
break), and apply the source's own disclosed MA-position gate directly:
only take the breakout long entry if yesterday's close was BELOW the 9-day
SMA (the source's own "more favorable" state for an upward breakout).
Exit on close falling back below the breakout support level (Donchian low)
or a max_hold_days time-stop. A close>SMA(trend_window) uptrend gate is
added (not in source) since Bulkowski's study spans full market history
without our repo's convention of a broader macro trend filter.

This is DISTINCT from every other Donchian/N-day-high breakout entry
already in this repo's knowledge base (checked via strategies_index.jsonl
grep for "N-Day High Breakout"/"Donchian"/"52-Week High" -- all existing
entries use the MA purely as a trend-following crossover/regime trigger or
omit the MA filter entirely; none use the MA-position-the-day-BEFORE-the-
breakout as a contrarian pre-condition per Bulkowski's disclosed empirical
finding).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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
    donchian_window: int = 20,
    ma_filter_window: int = 9,
    trend_sma_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # Donchian channel (excludes current bar to avoid look-ahead: shift(1))
    donchian_high = high.rolling(donchian_window).max().shift(1)
    donchian_low = low.rolling(donchian_window).min().shift(1)

    ma9 = close.rolling(ma_filter_window).mean()
    below_ma9_yesterday = (close.shift(1) < ma9.shift(1))

    trend_sma = close.rolling(trend_sma_window, min_periods=max(20, trend_sma_window // 4)).mean()
    uptrend_gate = close > trend_sma

    breakout = close > donchian_high
    entry = breakout & below_ma9_yesterday & uptrend_gate
    exit_support = close < donchian_low

    pos_vals = []
    in_pos = False
    hold_count = 0
    for i in range(len(close)):
        if not in_pos and bool(entry.iloc[i]):
            in_pos = True
            hold_count = 0
        elif in_pos:
            hold_count += 1
            if bool(exit_support.iloc[i]) or hold_count >= max_hold_days:
                in_pos = False
        pos_vals.append(1 if in_pos else 0)

    return pd.Series(pos_vals, index=close.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    donchian_window: int = 20,
    ma_filter_window: int = 9,
    trend_sma_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        donchian_window=donchian_window,
        ma_filter_window=ma_filter_window,
        trend_sma_window=trend_sma_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = (position.shift(1).fillna(0) * daily_ret).fillna(0.0)
    return strat_ret

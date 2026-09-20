"""Strategy: On Neck candlestick pattern, filtered for Bulkowski's
disclosed best-performing conditioning factors (tall bar1 candle + near
yearly low), tested as a BULLISH REVERSAL (the source's own
best-performing combination).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-168):
Per Thomas Bulkowski's Encyclopedia of Candlestick Charts summary
(https://www.thepatternsite.com/OnNeck.html, freely available), the On
Neck pattern is a 2-candle setup: a TALL black/bearish candle (bar1) in a
downtrend, followed by a white/bullish candle (bar2) whose close matches
(or nearly matches) bar1's low. Theoretically a bearish continuation
signal, Bulkowski's own testing found it continues bearishly only 56% of
the time ("near random"), BUT the source discloses that the single
BEST-performing combination across all his candlestick statistics is an
UPWARD breakout in a bear market after this pattern (average 10-day move
+8.32%, 10-day performance rank 6 out of 103 -- very high), and that
performance is materially better when (a) bar1 is a "tall" candle
(above-average true range) and (b) the pattern appears within a third of
the trailing yearly low. This strategy operationalizes that specific
best-performing combination as a long entry: On Neck pattern + tall bar1 +
near yearly low => long. 0 prior On Neck entries in this repo, distinct
from every other candlestick-close-matches-prior-extreme pattern already
tested (this is close MATCHING low, not gapping through or past it).

Signal logic
------------
- Downtrend filter: close[t-1] < close[t-1 - trend_lookback].
- Bar1 (t-1) bearish AND tall: close[t-1] < open[t-1], AND bar1's true
  range (high[t-1]-low[t-1]) >= tall_mult * its own trailing
  atr_window-bar average true range (evaluated using data up to and
  including t-2 to avoid leaking bar1's own range into its baseline).
- Bar2 (t) close matches bar1's low: |close[t] - low[t-1]| <=
  match_tolerance * low[t-1].
- Near-yearly-low filter: low[t-1] is within near_low_pct of the trailing
  252-bar rolling minimum low (i.e. "within a third of the yearly low" is
  operationalized generously as `near_low_pct` of the 252d range above the
  yearly low, default 0.33 per Bulkowski's own "within a third").
- Entry: long at bar t's own close once all of the above hold.
- Exit: close falls below its own SMA(exit_sma_window) OR max_hold_days
  reached, whichever first (same defensive exit pattern as the sibling
  candlestick strategies in this repo).

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
    tall_mult: float = 1.2,
    atr_window: int = 20,
    match_tolerance: float = 0.01,
    near_low_pct: float = 0.33,
    yearly_window: int = 252,
    exit_sma_window: int = 10,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    open_ = df["open"]
    close = df["close"]
    high = df["high"]
    low = df["low"]

    prior_close_shift = close.shift(trend_lookback)
    downtrend = close.shift(1) < prior_close_shift

    bar1_bearish = close.shift(1) < open_.shift(1)

    true_range = (high - low).abs()
    avg_range = true_range.shift(2).rolling(atr_window).mean()  # excludes bar1 (t-1) itself
    bar1_tall = true_range.shift(1) >= tall_mult * avg_range.shift(1)

    bar2_matches_low = (close - low.shift(1)).abs() <= match_tolerance * low.shift(1)

    yearly_low = low.rolling(yearly_window, min_periods=20).min()
    yearly_high = high.rolling(yearly_window, min_periods=20).max()
    yearly_range = (yearly_high - yearly_low).replace(0, pd.NA)
    near_yearly_low = ((low.shift(1) - yearly_low.shift(1)) / yearly_range.shift(1)) <= near_low_pct

    pattern_confirmed = (
        downtrend.fillna(False)
        & bar1_bearish.fillna(False)
        & bar1_tall.fillna(False)
        & bar2_matches_low.fillna(False)
        & near_yearly_low.fillna(False)
    )

    exit_sma = close.rolling(exit_sma_window).mean()

    position = pd.Series(0, index=idx, dtype=int)
    in_position = False
    entry_i = -1
    for i in range(n):
        if in_position:
            hold_days = i - entry_i
            trend_exit = close.iloc[i] < exit_sma.iloc[i] if pd.notna(exit_sma.iloc[i]) else False
            if trend_exit or hold_days >= max_hold_days:
                in_position = False
            else:
                position.iloc[i] = 1
        else:
            if bool(pattern_confirmed.iloc[i]):
                in_position = True
                entry_i = i
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_lookback: int = 10,
    tall_mult: float = 1.2,
    atr_window: int = 20,
    match_tolerance: float = 0.01,
    near_low_pct: float = 0.33,
    yearly_window: int = 252,
    exit_sma_window: int = 10,
    max_hold_days: int = 10,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        trend_lookback=trend_lookback,
        tall_mult=tall_mult,
        atr_window=atr_window,
        match_tolerance=match_tolerance,
        near_low_pct=near_low_pct,
        yearly_window=yearly_window,
        exit_sma_window=exit_sma_window,
        max_hold_days=max_hold_days,
    )
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

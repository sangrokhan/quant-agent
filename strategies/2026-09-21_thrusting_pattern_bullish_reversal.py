"""Strategy: Thrusting Pattern candlestick -- tested as a BULLISH REVERSAL
(per Bulkowski's own empirical finding, not the "textbook" bearish
continuation theory).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-167):
Per Thomas Bulkowski's Encyclopedia of Candlestick Charts summary
(https://www.thepatternsite.com/Thrusting.html, freely available), the
Thrusting Candlestick is a 2-candle pattern: in a downtrend, a black/bearish
candle (bar1) is followed by a white/bullish candle (bar2) that OPENS BELOW
bar1's low (a gap-down open, even more extreme than the Piercing Pattern's
gap) but closes NEAR-BUT-BELOW the midpoint of bar1's real body (i.e. it
does NOT reach the midpoint, unlike Piercing Pattern which requires closing
ABOVE the midpoint -- already tested/accepted in this repo as
2026-09-21-166, QQQ only). Theoretically this incomplete reversal is
supposed to signal BEARISH CONTINUATION, but Bulkowski's own large-sample
testing found it instead acts as a BULLISH REVERSAL 57% of the time
(frequency rank 56/103, overall performance rank 15/103 -- a fairly
high-ranked pattern despite the "near random" directional call). This
strategy tests the empirically-observed bullish-reversal behavior directly
(long entry), not the textbook theory. 0 prior Thrusting Pattern entries in
this repo, distinct calculation basis (BELOW midpoint) from
Piercing (ABOVE midpoint) and Bullish Engulfing (full-body reversal).

Signal logic
------------
- Downtrend filter: close[t-1] < close[t-1 - trend_lookback].
- Bar1 (t-1) bearish: close[t-1] < open[t-1].
- Bar2 (t) opens below bar1's own low: open[t] < low[t-1].
- Bar2 closes NEAR-BUT-BELOW bar1's body midpoint: close[t] is within
  `near_pct` of the midpoint from below, i.e.
  midpoint*(1-near_pct) <= close[t] < midpoint, where
  midpoint = (open[t-1]+close[t-1])/2. This distinguishes Thrusting
  (close BELOW midpoint) from Piercing (close ABOVE midpoint).
- Entry: long at bar t's own close once all of the above hold.
- Exit: close falls below its own SMA(exit_sma_window) OR max_hold_days
  reached, whichever first (same defensive exit pattern as the sibling
  Piercing Pattern strategy).

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
    near_pct: float = 0.5,
    exit_sma_window: int = 10,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    open_ = df["open"]
    close = df["close"]
    low = df["low"]

    prior_close_shift = close.shift(trend_lookback)
    downtrend = close.shift(1) < prior_close_shift

    bar1_bearish = close.shift(1) < open_.shift(1)
    bar2_gap_below_low = open_ < low.shift(1)

    bar1_open = open_.shift(1)
    bar1_close = close.shift(1)
    midpoint = (bar1_open + bar1_close) / 2.0
    # near-but-below midpoint: within near_pct of the [bar1_close, midpoint]
    # range, staying strictly below midpoint (distinguishes from Piercing).
    lower_bound = midpoint - near_pct * (midpoint - bar1_close).abs()
    bar2_near_midpoint_below = (close >= lower_bound) & (close < midpoint)

    pattern_confirmed = (
        downtrend.fillna(False)
        & bar1_bearish.fillna(False)
        & bar2_gap_below_low.fillna(False)
        & bar2_near_midpoint_below.fillna(False)
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
    near_pct: float = 0.5,
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
        near_pct=near_pct,
        exit_sma_window=exit_sma_window,
        max_hold_days=max_hold_days,
    )
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

"""Strategy: Piercing Pattern candlestick reversal (classic 2-candle bullish
reversal, with a trend/gap/midpoint confirmation and a time/trend-based
exit).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-166):
Per Investopedia's "Piercing Pattern Explained" (freely available, not
paywalled -- https://www.investopedia.com/piercing-pattern-explained-8747555),
a Piercing Pattern is a classic 2-candle bullish reversal signal:
  1. Preceded by a downtrend.
  2. Day 1 (bar t-1) is a bearish/red candle (close < open).
  3. Day 2 (bar t) gaps DOWN at the open (open[t] < close[t-1], usually also
     below low[t-1]) then rallies to close ABOVE the MIDPOINT of day 1's
     real body: close[t] > (open[t-1] + close[t-1]) / 2, but importantly
     close[t] < open[t-1] (does NOT fully engulf bar1 -- that would be a
     bullish engulfing pattern instead, a different already-tested repo
     strategy).
This is distinct from every prior candlestick strategy in this repo (0
prior "piercing pattern"/"piercing line" hits in strategies_index.jsonl):
unlike Bullish Engulfing (2026-09-21-161, full-body engulfment) this
requires a GAP DOWN open plus a MIDPOINT-only close recovery (partial, not
full, reversal of bar1's body) -- a materially different two-candle
geometry. Entry is at bar t's own close (the pattern is fully formed and
confirmed intraday-to-close, no extra day of confirmation needed per the
source's own definition, unlike Bullish Engulfing which needed a 3rd-bar
breakout confirmation). Exit uses a max_hold_days time-stop OR close
dropping back below its own short SMA (trend invalidation), whichever
comes first.

Signal logic
------------
- Downtrend filter: close[t-1] < close[t-1 - trend_lookback] (a decline
  over the preceding window, evaluated as of bar1 so we don't leak bar2's
  own info into the trend judgment).
- Bar1 (t-1) bearish: close[t-1] < open[t-1].
- Bar2 (t) gap-down open: open[t] < close[t-1] * (1 - gap_pct) (a
  meaningful gap, not a trivial fractional-cent gap).
- Bar2 midpoint-close recovery: close[t] > (open[t-1] + close[t-1]) / 2.0
  AND close[t] < open[t-1] (partial, not full, reversal -- distinguishes
  from Bullish Engulfing).
- Entry: long at bar t's own close once all of the above hold on bar t.
- Exit: close falls below its own SMA(exit_sma_window) OR max_hold_days
  reached, whichever first.

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
    gap_pct: float = 0.0,
    exit_sma_window: int = 10,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    open_ = df["open"]
    close = df["close"]

    prior_close_shift = close.shift(trend_lookback)
    downtrend = close.shift(1) < prior_close_shift

    bar1_bearish = close.shift(1) < open_.shift(1)
    bar2_gap_down = open_ < close.shift(1) * (1 - gap_pct)
    bar1_midpoint = (open_.shift(1) + close.shift(1)) / 2.0
    bar2_midpoint_close = (close > bar1_midpoint) & (close < open_.shift(1))

    pattern_confirmed = (
        downtrend.fillna(False)
        & bar1_bearish.fillna(False)
        & bar2_gap_down.fillna(False)
        & bar2_midpoint_close.fillna(False)
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
    gap_pct: float = 0.0,
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
        gap_pct=gap_pct,
        exit_sma_window=exit_sma_window,
        max_hold_days=max_hold_days,
    )
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

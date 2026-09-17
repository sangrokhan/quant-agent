"""Strategy: "Close Below Prior Low" dip-buy with next-up-close exit
(daily and weekly-signal variants disclosed by SetupAlpha).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD, this iteration):
Per SetupAlpha's "I Tested 5 'Buy The Dip' Candle Patterns on SPY" (2026-07-12,
https://setup4alpha.substack.com/p/tested-5-buy-the-dip-patterns-spy, read
this iteration via browser_exec after web_search DDGS backend returned only
generic/irrelevant SEO results for candle-pattern search queries): among 5
tested "buy the dip" candle patterns on SPY 2000-2026, the source fully
discloses the exact entry rule and exit rule for its 3 WEAKER patterns
(paywalling only the 2 stronger winners): Rule 1 (daily) = Close < Low[1]
(today's close undercuts yesterday's low, "catching a falling knife"); Rule 2
(weekly) = the same C<L[1] condition evaluated on weekly bars. BOTH share the
source's own disclosed exit: close > close[1] (exit on the very next up-close,
i.e. first sign of a bounce) -- deliberately simple, no moving averages or
trailing stops, to isolate the raw pattern edge. Source's own reported daily
numbers (66.51%/61.10%/64.13% win rates, but CAR only 1.5-4.5%, underperforms
buy-and-hold) motivate testing whether a trend-regime gate (only take the dip
entry when price is already above its own longer SMA, i.e. "buy dips in an
uptrend" rather than any dip) recovers the Sharpe this repo requires, since
the source's own raw ungated version clearly does not beat buy-and-hold.
First "close below prior bar's low" pattern-based mean-reversion entry in
this repo with this exact "close > close[1]" exit rule (distinct from IBS,
Bollinger, RSI2, or z-score mean-reversion families already tested, which all
use a normalized/derived oscillator rather than a raw single-bar low-undercut
condition as the trigger).

Signal logic
------------
- Entry (long): today's close < yesterday's low (daily variant, use_weekly=False)
  OR, if use_weekly=True, the same C<L[1] condition evaluated on the trailing
  weekly-resampled bar (approximated here as a rolling 5-day window used as
  the "weekly" bar, since this repo's loaders only provide daily OHLCV).
  Gated by close > SMA(trend_window) when trend_gate=True (source's own raw
  version has no trend gate; this repo tests the gated variant as the fix for
  the source's own reported CAR underperformance).
- Exit: close > close[1] (first up-close), or max_hold_days safety backstop.
- Long-only, flat otherwise, single position at a time.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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
    use_weekly: bool = False,
    weekly_window: int = 5,
    trend_gate: bool = True,
    trend_window: int = 150,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    n = len(close)

    if use_weekly:
        # Approximate "weekly" prior-bar low as the rolling weekly_window
        # low shifted by weekly_window (a completed prior weekly-equivalent
        # window), since this repo has no native weekly resample helper.
        prior_low = low.rolling(weekly_window).min().shift(weekly_window)
    else:
        prior_low = low.shift(1)

    entry = close < prior_low
    entry = entry.fillna(False)

    if trend_gate:
        sma = close.rolling(trend_window, min_periods=trend_window).mean()
        entry = entry & (close > sma)
        entry = entry.fillna(False)

    prev_close = close.shift(1)

    pos = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(n):
        if in_pos:
            held = i - entry_idx
            # Exit on first up-close (close > prior close) since entry, or time-stop.
            up_close = close.iloc[i] > close.iloc[i - 1] if i > 0 else False
            if up_close or held >= max_hold_days:
                in_pos = False
            else:
                pos.iloc[i] = 1
        if not in_pos and bool(entry.iloc[i]):
            in_pos = True
            entry_idx = i
            pos.iloc[i] = 1
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    use_weekly: bool = False,
    weekly_window: int = 5,
    trend_gate: bool = True,
    trend_window: int = 150,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return daily strategy returns (position lagged 1 day to avoid look-ahead)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        use_weekly=use_weekly,
        weekly_window=weekly_window,
        trend_gate=trend_gate,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret

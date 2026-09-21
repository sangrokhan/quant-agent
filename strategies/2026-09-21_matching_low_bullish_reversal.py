"""Strategy: Matching Low candlestick bullish reversal pattern.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-21-218):
Per QuantifiedStrategies.com's "Matching Low Candlestick Pattern: Backtest
Findings" (https://www.quantifiedstrategies.com/matching-low-candlestick-pattern/,
read via browser_exec this iteration -- web_search's DDGS backend returned
usable Google-style results this time, but the article's full text was
fetched via browser_exec since web_extract's ddgs backend cannot extract
page content) and corroborated by ForexBee/StockGro/WR Trading, the
"Matching Low" pattern is a 2-candle bullish-reversal candlestick setup
occurring during a downswing:

    - Bar1 (t-1): a long bearish candle (close < open), continuing the
      prevailing downtrend.
    - Bar2 (t): a SMALLER bearish candle (close < open, smaller real body
      than bar1) that opens HIGHER than bar1's close (a small gap up from
      the prior close) but then closes at (or within a small tolerance of)
      bar1's own close -- i.e. both candles' CLOSES nearly match, even
      though bar2 gapped up intraday. This "identical closes despite the
      gap up" signals sellers failing to push price to a new low, a sign
      the downside momentum is exhausted.
    - Source's own disclosed confirmation rule: wait for a bullish
      candle to follow before entering (rather than trading the raw
      2-candle pattern blind), since "in reality the matching low pattern
      acts as a continuation pattern to the downside more often" without
      that filter.
    - Source's own disclosed exit: a fixed N-bar time-stop (article states
      "we exit the trade after 5 bars" as its baseline backtest rule).

This is a genuinely new pattern for this repo (0 prior "matching low" hits
in strategies_index.jsonl) -- distinct from Bullish Harami (bar2 fully
CONTAINED inside bar1's body, no matching-close requirement), Piercing
Pattern (bar2 is bullish and closes above bar1's midpoint, not matching
bar1's close), and Tweezer Bottom (matches on LOWS, not closes, and does
not require both candles to be bearish).

Signal logic (long-only implementation)
----------------------------------------
- Downtrend filter: close[t-2] < close[t-2 - trend_lookback] (pattern must
  occur after a genuine downswing, per every source's stated context).
- Bar1 (t-1) bearish: close[t-1] < open[t-1].
- Bar2 (t) bearish and smaller-bodied than bar1: close[t] < open[t] AND
  abs(close[t]-open[t]) <= abs(close[t-1]-open[t-1]).
- Bar2 opens above bar1's close (the small gap-up): open[t] > close[t-1].
- Matching closes: abs(close[t] - close[t-1]) <= match_tolerance_pct *
  close[t-1] (source's "identical closes" criterion, tolerance-banded for
  daily-bar noise since exact equality never occurs in real data).
- Confirmation (source's own disclosed filter against the pattern's
  documented tendency to act as a downside continuation more often than a
  reversal): entry only on the first bullish confirmation candle
  (close > open) within confirm_window bars after bar2, entering at that
  candle's close.
- Exit: source's own disclosed fixed-bar-count exit (max_hold_days, default
  5) -- no indicator-based exit condition, per the article's stated
  baseline backtest methodology.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  {0,1} position series
    generate_returns(price_df, **params) -> pd.Series  daily strategy returns
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
    match_tolerance_pct: float = 0.003,
    confirm_window: int = 3,
    max_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    n = len(close)

    position = pd.Series(0, index=close.index, dtype=int)

    bar1_bearish = close.shift(1) < open_.shift(1)
    bar2_bearish = close < open_
    bar1_body = (open_.shift(1) - close.shift(1)).abs()
    bar2_body = (open_ - close).abs()
    bar2_smaller = bar2_body <= bar1_body
    bar2_gap_up_open = open_ > close.shift(1)
    matching_closes = (close - close.shift(1)).abs() <= match_tolerance_pct * close.shift(1).abs()
    downtrend = close.shift(2) < close.shift(2 + trend_lookback)

    pattern_at_t = (
        bar1_bearish
        & bar2_bearish
        & bar2_smaller
        & bar2_gap_up_open
        & matching_closes
        & downtrend.fillna(False)
    ).fillna(False)

    bullish_confirm = close > open_

    in_position = False
    hold_days_left = 0
    pending_pattern_bar = None  # index position of most recent unconfirmed pattern

    for i in range(n):
        if in_position:
            position.iloc[i] = 1
            hold_days_left -= 1
            if hold_days_left <= 0:
                in_position = False
            continue

        # Check if a pattern completed at this bar (bar2 = i); start looking
        # for confirmation starting next bar.
        if pattern_at_t.iloc[i]:
            pending_pattern_bar = i

        if pending_pattern_bar is not None:
            bars_since = i - pending_pattern_bar
            if 0 < bars_since <= confirm_window:
                if bool(bullish_confirm.iloc[i]):
                    in_position = True
                    hold_days_left = max_hold_days
                    position.iloc[i] = 1
                    pending_pattern_bar = None
                    continue
            elif bars_since > confirm_window:
                pending_pattern_bar = None

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

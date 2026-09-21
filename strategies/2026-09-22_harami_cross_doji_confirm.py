"""Strategy: Bullish Harami Cross (strict doji second-candle variant) with a
confirmation-candle entry trigger, on a downtrend gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-015):
Per Capital.com's Harami Cross explainer
(https://capital.com/en-int/learn/technical-analysis/harami-cross-pattern,
visited this iteration): a Harami Cross is a stricter variant of the
standard Harami pattern -- the second candle must be a true DOJI (open and
close nearly identical), not merely any small-bodied candle, and its body
(here collapsed to a single point given doji_tolerance) must sit entirely
within the first candle's body. The source explicitly recommends NOT
trading the raw 2-bar pattern alone, but waiting for a subsequent
confirmation candle closing in the anticipated reversal direction before
entering, with a stop beyond the first candle's extreme.

This repo already has a plain Bullish Harami strategy (2026-09-06-150,
which allows ANY small second-candle body <= harami_body_ratio x first
body). This strategy is distinct: it requires the second candle to be a
strict doji (much tighter body-to-range ratio) AND requires a third,
confirming bullish candle before entry (the source's own stated best
practice), rather than entering on the harami bar itself.

Signal logic
------------
- Downtrend gate: close < SMA(trend_window).
- Bar1 (mother candle): large bearish body, |body| >= min_body_atr_mult *
  ATR(atr_window) (a "substantial" bearish candle per the source).
- Bar2 (doji): |close - open| <= doji_tolerance * (high - low) for that bar
  (near-identical open/close), AND max(open, close) <= max(bar1 open,
  close) AND min(open, close) >= min(bar1 open, close) (doji body fully
  contained in bar1's body).
- Bar3 (confirmation, within confirm_window bars after the doji): a
  bullish candle (close > open) that closes above bar2's high.
- Entry (long): at bar3's close (the confirmation bar).
- Exit: close falls below bar1's low (stop-loss per the source's own
  recommended placement), close breaks back below SMA(trend_window)
  (trend-gate flip), or after max_hold_days (time-stop).
- Flat otherwise.

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


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    atr_window: int = 14,
    min_body_atr_mult: float = 0.8,
    doji_tolerance: float = 0.1,
    confirm_window: int = 3,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]

    sma_trend = close.rolling(trend_window).mean()
    downtrend = close < sma_trend

    atr = _atr(high, low, close, atr_window)
    bar1_body = (open_ - close)  # positive when bearish
    bar1_is_bearish_big = (bar1_body > 0) & (bar1_body >= min_body_atr_mult * atr)

    bar_range = (high - low).replace(0.0, 1e-12)
    is_doji = (close - open_).abs() <= (doji_tolerance * bar_range)

    bar1_body_hi = pd.concat([open_.shift(1), close.shift(1)], axis=1).max(axis=1)
    bar1_body_lo = pd.concat([open_.shift(1), close.shift(1)], axis=1).min(axis=1)
    bar2_hi = pd.concat([open_, close], axis=1).max(axis=1)
    bar2_lo = pd.concat([open_, close], axis=1).min(axis=1)
    doji_contained = (bar2_hi <= bar1_body_hi) & (bar2_lo >= bar1_body_lo)

    harami_cross_bar = (
        downtrend.shift(1).fillna(False)
        & bar1_is_bearish_big.shift(1).fillna(False)
        & is_doji.fillna(False)
        & doji_contained.fillna(False)
    )

    bar1_low_at_pattern = low.shift(1)  # bar1's low, aligned to bar2's index
    bar2_high = high  # bar2 (doji bar)'s high, for confirmation breakout level

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = None
    pattern_pending_until = -1
    pattern_bar1_low = None
    pattern_bar2_high = None

    for i in range(n):
        if in_position:
            held = i - entry_idx
            stop_hit = bool(close.iloc[i] < stop_level) if stop_level is not None else False
            trend_flip = not bool(downtrend.iloc[i])
            if stop_hit or trend_flip or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        # Check for confirmation of a pending pattern.
        if i <= pattern_pending_until and pattern_bar2_high is not None:
            is_bullish = close.iloc[i] > open_.iloc[i]
            confirms = is_bullish and close.iloc[i] > pattern_bar2_high
            if confirms:
                in_position = True
                entry_idx = i
                stop_level = pattern_bar1_low
                position.iloc[i] = 1
                pattern_bar2_high = None
                continue

        # Check for a fresh harami-cross bar today (bar2).
        if bool(harami_cross_bar.iloc[i]):
            pattern_bar1_low = float(bar1_low_at_pattern.iloc[i])
            pattern_bar2_high = float(bar2_high.iloc[i])
            pattern_pending_until = i + confirm_window

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

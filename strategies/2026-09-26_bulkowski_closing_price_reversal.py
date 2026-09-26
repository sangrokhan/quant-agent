"""Strategy: Bulkowski Closing Price Reversal (CPR), Downtrend variant.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Thomas Bulkowski, https://thepatternsite.com/CPRD.html (visited this
iteration): a single-bar pattern (uses today's bar plus yesterday's close)
that signals a reversal after a short-term downtrend. Rules: (1) short-term
downtrend context (close below its own SMA(trend_window)); (2) today's OPEN
is within `edge_pct` (25% per source) of today's intraday low; (3) today's
CLOSE is within `edge_pct` of today's intraday high AND above yesterday's
close. Source's own trading tip: buy at the next day's open; measure rule
(fulfilled 72% of the time in the source's own 1990-2013, 1199-stock bull-
market backtest) sets a profit target of pattern-height added to the
pattern's high. First Closing Price Reversal pattern tested in this repo --
distinct from Outside Day (high>prior high AND low<prior low) and candlestick
reversal patterns (body-relative, not open/close-vs-range-relative) already
tested here.

Signal logic
------------
- Trend context: close below its own SMA(trend_window) (source's "short-term
  downtrend"), or trend_window<=0 to disable.
- Pattern bar: open within edge_pct of the day's low AND close within
  edge_pct of the day's high AND close > prior day's close.
- Entry: NEXT bar's open (source's own "buy at the open the next day").
  Approximated at next bar's close in this repo's daily-close-return
  contract (no intrabar/open-price fills available to generate_returns).
- Exit: close >= entry_price + height_mult * pattern_height (source's
  measure-rule target, height = pattern bar's high-low range), OR a
  max_hold_days time-stop as a backstop (source doesn't specify a max hold
  but doesn't rule one out either -- this repo's convention).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    trend_window: int = 50,
    edge_pct: float = 0.25,
    height_mult: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]

    rng = (high - low).replace(0, pd.NA)
    open_near_low = (open_ - low) / rng <= edge_pct
    close_near_high = (high - close) / rng <= edge_pct
    close_above_prior = close > close.shift(1)

    if trend_window and trend_window > 0:
        sma = close.rolling(trend_window).mean()
        trend_down = close < sma
    else:
        trend_down = pd.Series(True, index=close.index)

    pattern_confirmed = (
        open_near_low & close_near_high & close_above_prior & trend_down
    ).fillna(False)

    pattern_height = (high - low)
    entry_trigger = pattern_confirmed.shift(1).fillna(False)  # enter next bar
    height_level = pattern_height.shift(1)
    pattern_high_level = high.shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    target_level = None
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            hit_target = (target_level is not None) and (close.iloc[i] >= target_level)
            if hit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                target_level = None
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                h = height_level.iloc[i]
                base = pattern_high_level.iloc[i]
                target_level = (base + height_mult * h) if pd.notna(h) and pd.notna(base) else None
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

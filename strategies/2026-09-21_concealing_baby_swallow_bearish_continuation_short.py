"""Strategy: Concealing Baby Swallow bearish continuation (short).

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration):
Per QuantifiedStrategies.com's "75 Types of Candlestick Patterns" list
(https://www.quantifiedstrategies.com/types-candlestick-patterns/, read via
browser_exec fallback -- web_extract ddgs backend cannot extract page
content), the "Concealing Baby Swallow" is a 4-candle pattern forming in a
downtrend. TRADITIONALLY seen as a bullish reversal pattern, but the
source's own disclosed reading is that "a lot of traders actually consider
this one a bearish continuation pattern" -- this strategy operationalizes
that empirically-favored bearish-continuation reading (matching this
iteration's earlier pattern for source-corrected labels: Unique Three
Rivers, Deliberation), per the source's exact identification rule:
  - Bar1, Bar2: both tall AND bearish.
  - Bar3: opens with a gap (down, continuing the bearish move), is ALSO
    bearish, and has a long upper wick.
  - Bar4: bearish, and completely ENGULFS bar3 (bar4's open >= bar3's
    high, bar4's close <= bar3's low).
Source's own interpretation: bears are completely in control, any
bullish attempt (bar3's failed upper-wick rejection) is met with massive
selling pressure (bar4's full engulf).

First Concealing Baby Swallow entry in this repo (0 prior hits) --
distinct from Three Black Crows (3 candles, no gap/engulf/wick structure)
and every other engulfing-family pattern already tested (this is a bar4-
engulfs-bar3 relationship, not the classic 2-candle Bearish Engulfing).

Signal logic
------------
- Downtrend filter: close[t-3] < close[t-3 - trend_lookback].
- Bar1 (t-3), Bar2 (t-2): both bearish (close<open) AND tall (body size
  >= tall_body_mult * trailing atr_window-bar average true range,
  computed excluding the pattern bars themselves).
- Bar3 (t-1) bearish AND gaps down from bar2: open[t-1] < close[t-2].
- Bar3 (t-1) has a long upper wick: (high[t-1] - max(open,close)[t-1]) >=
  upper_wick_mult * body size of bar3.
- Bar4 (t) bearish AND fully engulfs bar3: open[t] >= high[t-1] * (1 -
  engulf_tolerance) AND close[t] <= low[t-1] * (1 + engulf_tolerance).
- No numeric stop/target disclosed by the source -- this repo's standard
  ATR stop/target and max-hold-days backstop used.
- Entry: short at bar t's own close once all of the above hold.
- Exit: close rises above its own SMA(exit_sma_window) OR the ATR
  target/stop is hit OR max_hold_days reached, whichever first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 short-position
    flag, matching this repo's established short-strategy convention).
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
    tall_body_mult: float = 0.8,
    upper_wick_mult: float = 0.5,
    engulf_tolerance: float = 0.005,
    atr_window: int = 20,
    exit_sma_window: int = 10,
    atr_stop_mult: float = 2.0,
    target_atr_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} short-position-flag series (1 = actively short)."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    open_ = df["open"]
    close = df["close"]
    high = df["high"]
    low = df["low"]

    downtrend = close.shift(3) < close.shift(3 + trend_lookback)

    bar1_bearish = close.shift(3) < open_.shift(3)
    bar2_bearish = close.shift(2) < open_.shift(2)

    true_range = (high - low).abs()
    avg_range = true_range.shift(4).rolling(atr_window).mean()

    body1 = (open_.shift(3) - close.shift(3)).abs()
    body2 = (open_.shift(2) - close.shift(2)).abs()
    bar1_tall = body1 >= tall_body_mult * avg_range.shift(3)
    bar2_tall = body2 >= tall_body_mult * avg_range.shift(2)

    bar3_bearish = close.shift(1) < open_.shift(1)
    bar3_gap_down = open_.shift(1) < close.shift(2)
    body3 = (open_.shift(1) - close.shift(1)).abs()
    max_oc3 = pd.concat([open_.shift(1), close.shift(1)], axis=1).max(axis=1)
    upper_wick3 = high.shift(1) - max_oc3
    body3_safe = body3.replace(0, float("nan"))
    bar3_long_upper_wick = upper_wick3 >= upper_wick_mult * body3_safe

    bar4_bearish = close < open_
    bar4_engulfs = (open_ >= high.shift(1) * (1 - engulf_tolerance)) & (
        close <= low.shift(1) * (1 + engulf_tolerance)
    )

    pattern_confirmed = (
        downtrend.fillna(False)
        & bar1_bearish.fillna(False)
        & bar2_bearish.fillna(False)
        & bar1_tall.fillna(False)
        & bar2_tall.fillna(False)
        & bar3_bearish.fillna(False)
        & bar3_gap_down.fillna(False)
        & bar3_long_upper_wick.fillna(False)
        & bar4_bearish.fillna(False)
        & bar4_engulfs.fillna(False)
    )

    atr = true_range.rolling(atr_window).mean()

    position = pd.Series(0, index=idx, dtype=int)
    stop_price = None
    target_price = None
    hold_count = 0

    confirmed = pattern_confirmed.to_numpy()
    close_arr = close.to_numpy()
    atr_arr = atr.to_numpy()
    sma_exit = close.rolling(exit_sma_window).mean().to_numpy()

    in_position = False
    for i in range(n):
        if in_position:
            hold_count += 1
            c = close_arr[i]
            exit_now = False
            if stop_price is not None and c >= stop_price:
                exit_now = True
            elif target_price is not None and c <= target_price:
                exit_now = True
            elif not pd.isna(sma_exit[i]) and c > sma_exit[i]:
                exit_now = True
            elif hold_count >= max_hold_days:
                exit_now = True
            if exit_now:
                in_position = False
                stop_price = target_price = None
                hold_count = 0
            else:
                position.iloc[i] = 1
                continue

        if not in_position and confirmed[i] and not pd.isna(atr_arr[i]) and atr_arr[i] > 0:
            in_position = True
            entry_price = close_arr[i]
            stop_price = entry_price + atr_stop_mult * atr_arr[i]
            target_price = entry_price - target_atr_mult * atr_arr[i]
            hold_count = 0
            position.iloc[i] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Daily strategy returns for a SHORT position: -1 * prior-day position
    * that day's simple return (position=1 means actively short)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = -1.0 * position.shift(1).fillna(0) * daily_ret
    return strat_ret

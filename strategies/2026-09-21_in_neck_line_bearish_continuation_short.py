"""Strategy: In Neck Line bearish continuation candlestick pattern (short).

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration):
Per QuantifiedStrategies.com's "75 Types of Candlestick Patterns"
(https://www.quantifiedstrategies.com/types-candlestick-patterns/, read via
browser_exec fallback -- web_extract ddgs backend cannot extract page
content), the "In Neck Line" is a 2-candle bearish CONTINUATION pattern in a
downtrend: bar1 is a long bearish candle; bar2 opens with a down-gap but
rallies to close AT OR SLIGHTLY ABOVE bar1's close (not at bar1's low, which
would instead be the already-tested On Neck Line, 2026-09-21-168/related).
The source's own interpretation: bulls attempted to push back but failed to
reach even the middle of bar1's body (which would instead be the bullish
Piercing Pattern reversal) -- confirming bears retain control, continuation
lower expected.

Distinct from every other candlestick-close-matches-prior-level pattern
already tested in this repo:
  - On Neck Line (bar2 closes at bar1's LOW, not bar1's CLOSE)
  - Matching Low (bar2 closes near bar1's close, but bar1 need not be a
    long/tall bearish candle and there's no explicit down-gap-then-rally
    requirement)
  - Piercing Pattern (bar2 closes ABOVE the midpoint of bar1's body -- the
    bullish-reversal outcome the In Neck Line source explicitly says did
    NOT happen here)

First In Neck Line entry in this repo (0 prior hits).

Signal logic
------------
- Downtrend filter: close[t-1] < close[t-1 - trend_lookback].
- Bar1 (t-1) bearish AND long: close[t-1] < open[t-1], AND bar1's body
  size (open[t-1]-close[t-1]) >= long_body_mult * its own trailing
  atr_window-bar average true range (computed excluding bar1 itself to
  avoid leakage).
- Bar2 (t) opens with a down-gap below bar1's close: open[t] < close[t-1].
- Bar2 (t) closes at-or-slightly-above bar1's close (the defining "in neck"
  feature, distinct from On Neck's close-at-bar1's-low):
  close[t-1] <= close[t] <= close[t-1] * (1 + match_tolerance).
- No numeric stop/target disclosed by the source -- this repo's standard
  ATR stop/target and max-hold-days backstop used.
- Entry: short at bar t's own close once all of the above hold.
- Exit: close rises above its own SMA(exit_sma_window) (trend-reversal
  invalidates the continuation thesis) OR the ATR target/stop is hit OR
  max_hold_days reached, whichever first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 short position
    series where 1 = short/-1-equivalent short exposure represented as a
    simple {0,1} "in a short position" flag, matching this repo's
    established short-strategy convention of generate_returns applying
    -1x the position's daily return).
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
    long_body_mult: float = 1.2,
    atr_window: int = 20,
    match_tolerance: float = 0.005,
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

    prior_close_shift = close.shift(trend_lookback)
    downtrend = close.shift(1) < prior_close_shift

    bar1_bearish = close.shift(1) < open_.shift(1)

    body1 = (open_.shift(1) - close.shift(1)).abs()
    true_range = (high - low).abs()
    avg_range = true_range.shift(2).rolling(atr_window).mean()
    bar1_long = body1 >= long_body_mult * avg_range.shift(1)

    down_gap = open_ < close.shift(1)
    bar2_in_neck = (close >= close.shift(1)) & (
        close <= close.shift(1) * (1 + match_tolerance)
    )

    pattern_confirmed = (
        downtrend.fillna(False)
        & bar1_bearish.fillna(False)
        & bar1_long.fillna(False)
        & down_gap.fillna(False)
        & bar2_in_neck.fillna(False)
    )

    atr = true_range.rolling(atr_window).mean()

    position = pd.Series(0, index=idx, dtype=int)
    entry_price = None
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
                entry_price = stop_price = target_price = None
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

"""Strategy: Bullish TriStar Doji reversal (long, breakout-confirmed).

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration):
Per QuantifiedStrategies.com's "Bullish TriStar Doji Candlestick Pattern"
(https://www.quantifiedstrategies.com/bullish-tristar-doji-candlestick-pattern/,
read via browser_exec fallback -- web_extract ddgs backend cannot extract
page content), the Bullish TriStar Doji is a rare 3-candle reversal
pattern in a downtrend: three CONSECUTIVE doji candlesticks (indicating
peak indecision). Source's own disclosed trading rule: wait for
CONFIRMATION -- entry on a later close breaking above the pattern's high
(the highest high of the 3 doji bars); stop-loss below the low of the
doji candlesticks (the pattern's lowest low); risk-reward ratio of at
least 1:2.

First TriStar Doji entry in this repo (0 prior hits) -- distinct from
Bullish Doji Star (2026-09-09-056, only ONE doji sandwiched between a
bearish and a bullish candle, not 3 consecutive dojis) and every other
doji-based pattern already tested (this requires 3 dojis IN A ROW, the
strongest possible "indecision cluster" signal in this repo's candlestick
family).

Signal logic
------------
- Downtrend filter: close[t-3] < close[t-3 - trend_lookback] (measured at
  the bar before the 3-doji cluster begins).
- Bars t-2, t-1, t: each is a doji (|close-open| <= doji_body_pct *
  (high-low), a small-or-no real body relative to its own range).
- Confirmation entry: on a LATER bar (t+k, k>=1) whose close breaks above
  the pattern's high (max(high[t-2:t+1])) -- entry_expiry_bars caps how
  many bars after the pattern the breakout confirmation is still valid
  (source gives no explicit expiry, this repo's standard backstop).
- Stop-loss: below the pattern's low (min(low[t-2:t+1])) -- source's own
  disclosed rule.
- Target: risk-reward >= 1:2 per the source's own stated ratio (target =
  entry + reward_ratio * (entry - stop)).
- Exit: stop hit, target hit, OR max_hold_days reached, whichever first.

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
    doji_body_pct: float = 0.10,
    entry_expiry_bars: int = 5,
    reward_ratio: float = 2.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    open_ = df["open"]
    close = df["close"]
    high = df["high"]
    low = df["low"]

    downtrend = close.shift(3) < close.shift(3 + trend_lookback)

    bar_range = (high - low).replace(0, float("nan"))
    body = (close - open_).abs()
    is_doji = (body / bar_range) <= doji_body_pct

    pattern_confirmed = (
        downtrend.fillna(False)
        & is_doji.shift(2).fillna(False)
        & is_doji.shift(1).fillna(False)
        & is_doji.fillna(False)
    )

    pattern_high = pd.concat([high.shift(2), high.shift(1), high], axis=1).max(axis=1)
    pattern_low = pd.concat([low.shift(2), low.shift(1), low], axis=1).min(axis=1)

    position = pd.Series(0, index=idx, dtype=int)

    confirmed = pattern_confirmed.to_numpy()
    close_arr = close.to_numpy()
    pattern_high_arr = pattern_high.to_numpy()
    pattern_low_arr = pattern_low.to_numpy()

    pending_high = None
    pending_low = None
    pending_expiry = 0
    stop_price = None
    target_price = None
    hold_count = 0
    in_position = False

    for i in range(n):
        if in_position:
            hold_count += 1
            c = close_arr[i]
            exit_now = False
            if stop_price is not None and c <= stop_price:
                exit_now = True
            elif target_price is not None and c >= target_price:
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

        if not in_position:
            if confirmed[i]:
                pending_high = pattern_high_arr[i]
                pending_low = pattern_low_arr[i]
                pending_expiry = entry_expiry_bars
            elif pending_expiry > 0:
                pending_expiry -= 1
                if pending_expiry <= 0:
                    pending_high = None
                    pending_low = None

            if pending_high is not None and not in_position:
                c = close_arr[i]
                if c > pending_high:
                    in_position = True
                    entry_price = c
                    stop_price = pending_low
                    risk = entry_price - stop_price
                    target_price = entry_price + reward_ratio * risk
                    hold_count = 0
                    pending_high = None
                    pending_low = None
                    position.iloc[i] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

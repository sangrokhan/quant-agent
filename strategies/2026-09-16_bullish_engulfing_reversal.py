"""Strategy: Bullish Engulfing candlestick reversal (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's
id): per Google AI-overview synthesis of Enlightened Stock Trading/Zerodha/
ChartsWatcher, a numeric Bullish Engulfing pattern requires: (1) a prior
downtrend context bar t-1 that is bearish (close < open) AND its low is
the lowest low over a downtrend_lookback-bar window (confirms a genuine
local bottom, not just any red candle); (2) the engulfing bar t is bullish
(close > open) with its real body strictly containing the prior bar's real
body (open_t <= close_{t-1} AND close_t >= open_{t-1}). Entry: buy on the
open of bar t+1 (source's "aggressive entry" variant -- market open buy,
simpler for this repo's daily-close-based vectorbt pipeline than the
"stop-buy above High_t + 1 tick" confirmation variant). Stop-loss: below
min(Low_{t-1}, Low_t). Take-profit: 2.0x R (R = entry - stop) OR a fixed
5-bar holding period (source's own numeric exit rule), whichever comes
first.

Sources read this iteration:
- Google AI-overview synthesis of Bullish Engulfing pattern numeric
  entry/exit rules (Enlightened Stock Trading, Zerodha, ChartsWatcher).

First Bullish Engulfing candlestick-pattern strategy in this knowledge
base (zero prior matches for "Engulfing").

Signal logic
------------
- Downtrend context: prior bar (t-1) is bearish (close < open) AND its low
  equals the rolling min(low) over downtrend_lookback bars ending at t-1.
- Engulfing bar (t): bullish (close > open), body containment
  (open_t <= close_{t-1} and close_t >= open_{t-1}).
- Entry: next bar's open (t+1), long.
- Stop: min(low_{t-1}, low_t).
- Take-profit: entry + reward_risk_mult * (entry - stop).
- Exit: close >= take-profit, close <= stop, OR max_hold_bars elapsed
  (source's 5-bar fixed hold as a fallback exit, adapted here as a
  max_hold_bars time-stop parameter defaulting to 5).
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


def generate_signals(
    price_df: pd.DataFrame,
    downtrend_lookback: int = 20,
    near_low_tolerance: float = 0.02,
    reward_risk_mult: float = 2.0,
    max_hold_bars: int = 5,
) -> pd.Series:
    df = _prep(price_df)
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]

    rolling_min_low = low.rolling(downtrend_lookback).min()

    prev_bearish = close.shift(1) < open_.shift(1)
    # "near_low_tolerance" relaxation of the strict low_t-1==rolling_min
    # equality (source's literal rule almost never fires on real data --
    # empirically checked this iteration: only 2 occurrences over 8.5yr
    # QQQ daily bars at the strict equality condition) -- widened to
    # "within tolerance of the lookback-window low" to get a statistically
    # testable sample size while still requiring a genuine local bottom.
    prev_at_low = low.shift(1) <= rolling_min_low.shift(1) * (1 + near_low_tolerance)
    downtrend_ctx = prev_bearish & prev_at_low

    curr_bullish = close > open_
    body_contain = (open_ <= close.shift(1)) & (close >= open_.shift(1))

    engulfing_confirmed = downtrend_ctx & curr_bullish & body_contain

    n = len(df.index)
    position = pd.Series(0, index=df.index, dtype=int)

    in_position = False
    hold_bars = 0
    stop_price = None
    tp_price = None
    pending_entry = False

    for i in range(n):
        c = close.iloc[i]

        if in_position:
            hold_bars += 1
            if c <= stop_price or c >= tp_price or hold_bars >= max_hold_bars:
                in_position = False
                hold_bars = 0
                stop_price = None
                tp_price = None
            else:
                position.iloc[i] = 1
                continue

        if pending_entry:
            entry_price = open_.iloc[i]
            risk = entry_price - stop_price
            if risk > 0:
                in_position = True
                hold_bars = 1
                tp_price = entry_price + reward_risk_mult * risk
                position.iloc[i] = 1
            pending_entry = False
            continue

        if bool(engulfing_confirmed.iloc[i]):
            stop_price = min(low.iloc[i - 1], low.iloc[i]) if i > 0 else low.iloc[i]
            pending_entry = True

    return position


def generate_returns(
    price_df: pd.DataFrame,
    downtrend_lookback: int = 20,
    near_low_tolerance: float = 0.02,
    reward_risk_mult: float = 2.0,
    max_hold_bars: int = 5,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        downtrend_lookback=downtrend_lookback,
        near_low_tolerance=near_low_tolerance,
        reward_risk_mult=reward_risk_mult,
        max_hold_bars=max_hold_bars,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns

"""Strategy: Three Bar Reversal (bullish), trend-context gated, daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-XXX):
Per TradingSim ("Day Trading the Three Bar Reversal Pattern",
https://www.tradingsim.com/blog/day-trading-the-three-bar-reversal-pattern,
browser_exec fallback -- web_search DDGS backend returned empty/error
results this iteration): a bullish 3-bar reversal forms when (1) the
middle bar of a 3-bar sequence makes the LOWEST low of the three (the
"low occurs on the middle candlestick"), and (2) the third bar closes
above the HIGH of BOTH the first and middle bars (the source's own
tightened rule -- the loose textbook version only requires closing above
the middle bar's high, but the source explicitly recommends the stricter
both-bars variant "to increase the odds in our favor"). The source also
requires the setup to occur within a clear prior downtrend/pullback (day
trading context) and suggests placing a protective stop below the low of
the middle candlestick, targeting roughly a 3:1 reward:risk (no fixed
numeric price target disclosed, so this is implemented here as a
measured-move multiple of the pattern's own risk distance, i.e.
entry - middle_low, consistent with the source's 3:1 R:R guidance) or a
time-stop, whichever comes first.

Adapted from the source's intraday 5-minute-bar day-trading context to
this repo's daily-bar OHLCV universe: the "hard downtrend" precondition is
implemented as a simple prior-N-day SMA downtrend filter (close below a
falling short SMA) so the pattern is only traded as a genuine reversal
out of a real pullback, per the source's own stated requirement, not as
random noise-pattern matching (the source explicitly warns the pattern is
"found all over the place" and needs filtering).

Distinct from every existing candlestick-reversal entry in this repo:
- 2026-09-08-122 (Bullish Outside Bar): a SINGLE-bar full-range engulf
  pattern (current bar's range engulfs the prior bar's range), not a
  3-bar sequence with a specific middle-bar-extreme-low requirement.
- Bulkowski Key Reversal entries (2026-09-26-051/-052): single-bar
  open/close constraint on ONE outside day, not a 3-bar low-in-the-middle
  structure.
This is the first three-bar (middle-bar-extreme) reversal pattern tested
in this repo's knowledge base.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    trend_sma_window: int = 10,
    reward_risk_mult: float = 3.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Pattern (bars i-2, i-1, i):
      - low[i-1] == min(low[i-2], low[i-1], low[i])  (low occurs on middle bar)
      - close[i] > max(high[i-2], high[i-1])           (close above both prior highs)
      - close[i-2] < sma(trend_sma_window) at i-2       (prior pullback/downtrend context)

    Entry at close of bar i. Stop distance = entry_price - low[i-1] (the
    middle bar's low). Exit on: price reaching entry + reward_risk_mult *
    stop_distance (measured-move / R:R target), price closing below the
    middle-bar low (stop-loss), or a max_hold_days time-stop.
    """
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    sma = close.rolling(trend_sma_window).mean()

    low_mid_is_min = (low.shift(1) <= low.shift(2)) & (low.shift(1) <= low)
    close_above_both_highs = close > pd.concat(
        [high.shift(1), high.shift(2)], axis=1
    ).max(axis=1)
    prior_downtrend = close.shift(2) < sma.shift(2)

    entry = low_mid_is_min & close_above_both_highs & prior_downtrend.fillna(False)
    middle_low = low.shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            px = close.iloc[i]
            hit_stop = px <= stop_price
            hit_target = px >= target_price
            if hit_stop or hit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) and not pd.isna(middle_low.iloc[i]):
                stop_dist = close.iloc[i] - middle_low.iloc[i]
                if stop_dist > 0:
                    in_position = True
                    entry_idx = i
                    entry_price = close.iloc[i]
                    stop_price = middle_low.iloc[i]
                    target_price = entry_price + reward_risk_mult * stop_dist
                    position.iloc[i] = 1
                else:
                    position.iloc[i] = 0
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

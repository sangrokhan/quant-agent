"""Strategy: Bulkowski Key Reversal, Downtrend -- long/up-breakout side.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Thomas Bulkowski, https://thepatternsite.com/KRD.html (visited this
iteration): a 2-bar pattern in a short-term downtrend -- an outside day
(today's high > prior day's high AND today's low < prior day's low) with two
ADDITIONAL positioning constraints: today's close > prior day's HIGH, and
today's open < prior day's CLOSE (i.e. the bar opens weak, inside/below the
prior close, but rallies hard enough to close above the prior day's entire
range). Source's own finding: despite the "reversal" framing, 51% of these
patterns actually continue lower -- so the source's own trading tip is
"trade in the breakout direction" (either way), same philosophy as this
repo's already-accepted Hook Reversal strategy
(2026-09-26_bulkowski_hook_reversal_breakout.py). This strategy trades ONLY
the long/up-breakout side (repo long-only convention): entry when a
SUBSEQUENT close breaks above the 2-bar pattern's high; measure-rule target
= pattern height added to the breakout level (met 69% of the time for up
breakouts per source's own 1990-2013, 1189-stock backtest). First Key
Reversal (Bulkowski's specific open/close-positioned outside-day variant)
tested in this repo -- more specific than the plain Outside Day pattern
already tested (2026-09-08-086, 2026-09-26-038) via the added open<prior-
close AND close>prior-high positioning constraints.

Signal logic
------------
- Trend context: close below its own SMA(trend_window) (source's "short-term
  downtrend"), or trend_window<=0 to disable.
- Pattern bar (today, vs prior day): outside day (high>prior high AND
  low<prior low) AND close>prior high AND open<prior close.
- Entry: NEXT bar's close breaks above the pattern's high (today's high,
  since today's high already exceeds the prior day's high by construction).
- Exit: close >= entry_price + height_mult * pattern_height (measure-rule
  target), OR a max_hold_days time-stop as a backstop.

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
    height_mult: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]

    outside_day = (high > high.shift(1)) & (low < low.shift(1))
    close_above_prior_high = close > high.shift(1)
    open_below_prior_close = open_ < close.shift(1)

    if trend_window and trend_window > 0:
        sma = close.rolling(trend_window).mean()
        trend_down = close < sma
    else:
        trend_down = pd.Series(True, index=close.index)

    pattern_confirmed = (
        outside_day & close_above_prior_high & open_below_prior_close & trend_down
    ).fillna(False)

    pattern_high = high  # today's high already exceeds prior day's by construction
    pattern_low = pd.concat([low, low.shift(1)], axis=1).min(axis=1)
    pattern_height = pattern_high - pattern_low

    breakout_trigger = pattern_confirmed.shift(1).fillna(False) & (close > pattern_high.shift(1))
    height_level = pattern_height.shift(1)
    pattern_high_level = pattern_high.shift(1)

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
            if bool(breakout_trigger.iloc[i]):
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

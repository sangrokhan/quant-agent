"""Strategy: Bulkowski Bullish Double-Key Reversal (3-bar pattern) breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Thomas Bulkowski, https://thepatternsite.com/DoubleKeyBull.html (visited
this iteration): in a short-term downtrend, a 3-bar sequence where (1) bar1
closes in the lower 25% of its own high-low range, (2) bar2 makes a LOWER
LOW than bar1 but closes ABOVE bar1's close, and (3) bar3 makes a LOWER LOW
than bar2 but closes ABOVE bar2's close -- i.e. price keeps probing lower
intrabar while closes keep recovering higher, a "double" failed-breakdown
signature distinct from a single Turtle-Soup-style failed breakdown -- marks
exhaustion of the downside probe and is worth a long entry on a breakout
above the pattern's high. Source's own disclosed rules: entry on a buy-stop
a penny above the pattern's highest bar; stop-loss a penny below the
pattern's lowest bar; target = 2x pattern height above the highest bar
(a fixed height-based profit target, not a moving-average exit). This is the
first Double-Key Reversal pattern tested in this repo -- structurally
distinct from Turtle Soup (single failed breakdown of an aged N-day level),
On Neck/Thrusting (2-candle patterns), and Outside Day (single-bar high>prior
high AND low<prior low) already tested here.

Signal logic
------------
- Trend context: close is below its own SMA(trend_window) at bar3 (source's
  "near-term downtrend" / "new low ground" qualifier), or trend_window<=0 to
  disable this gate.
- Bar1: close in the lower `body_pct` (default 0.25) of its own high-low
  range.
- Bar2: low < bar1's low, AND close > bar1's close.
- Bar3: low < bar2's low, AND close > bar2's close.
- Entry: next bar (bar4) trades above the pattern's high (max(high1,high2,
  high3)) -- breakout buy-stop, approximated here as an entry on bar4's close
  if bar4's high cleared the pattern high (can't literally place an
  intra-bar stop order with this repo's daily-close signal contract).
- Exit: close >= entry_price + height_mult * pattern_height (source's height
  target), OR close <= pattern_low (source's stop-loss, approximated at
  close rather than intrabar penny-below), OR a max_hold_days time-stop as a
  backstop (source doesn't specify one, but Bulkowski's own average holding
  periods are ~17-28 days, so this repo's convention of capping runaway
  holds is a reasonable, disclosed-hold-time-consistent addition).

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
    body_pct: float = 0.25,
    height_mult: float = 2.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]

    rng = (high - low).replace(0, pd.NA)
    close_pct_of_range = (close - low) / rng

    bar1_close_pct = close_pct_of_range.shift(2)
    bar1_close = close.shift(2)
    bar2_low, bar2_close = low.shift(1), close.shift(1)
    bar3_low, bar3_close = low, close

    bar1_cond = bar1_close_pct <= body_pct
    bar2_cond = (bar2_low < low.shift(2)) & (bar2_close > bar1_close)
    bar3_cond = (bar3_low < bar2_low) & (bar3_close > bar2_close)

    if trend_window and trend_window > 0:
        sma = close.rolling(trend_window).mean()
        trend_down = close < sma
    else:
        trend_down = pd.Series(True, index=close.index)

    pattern_confirmed = (bar1_cond & bar2_cond & bar3_cond & trend_down).fillna(False)
    pattern_high = pd.concat([high, high.shift(1), high.shift(2)], axis=1).max(axis=1)
    pattern_low = pd.concat([low, low.shift(1), low.shift(2)], axis=1).min(axis=1)
    pattern_height = pattern_high - pattern_low

    # Breakout confirmation on the NEXT bar after the pattern completes:
    # that bar's high must clear the pattern high (buy-stop trigger proxy).
    breakout_trigger = pattern_confirmed.shift(1).fillna(False) & (high > pattern_high.shift(1))
    entry_price_level = pattern_high.shift(1)
    stop_level_level = pattern_low.shift(1)
    height_level = pattern_height.shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = None
    stop_level = None
    target_level = None
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            hit_target = (target_level is not None) and (close.iloc[i] >= target_level)
            hit_stop = (stop_level is not None) and (close.iloc[i] <= stop_level)
            if hit_target or hit_stop or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                entry_price = stop_level = target_level = None
                continue
            position.iloc[i] = 1
        else:
            if bool(breakout_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
                stop_level = stop_level_level.iloc[i]
                h = height_level.iloc[i]
                target_level = entry_price + height_mult * h if pd.notna(h) else None
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

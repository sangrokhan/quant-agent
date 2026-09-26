"""Strategy: Bulkowski Hook Reversal, Downtrend (long/up-breakout side only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Thomas Bulkowski, https://thepatternsite.com/HRD.html (visited this
iteration): a 2-bar pattern in a short-term downtrend -- bar1 sets a range,
bar2 is an inside day (bar2's high < bar1's high AND bar2's low > bar1's
low), AND bar2's own open is within `edge_pct` of its intraday low while
bar2's own close is within `edge_pct` of its intraday high (an edge-position
filter on top of the plain inside-day structure). Source's own finding:
despite being framed as a "reversal", 51% of these patterns actually
continue lower -- so the source's own trading tip is "trade in the breakout
direction" rather than assume reversal. This strategy trades ONLY the long/
up-breakout side (repo convention, long-only): entry when close breaks above
the 2-bar pattern's high; measure-rule target = pattern height added to the
breakout level (met 69% of the time for up breakouts per source's own
1990-2013, 1201-stock backtest). First Hook Reversal pattern tested in this
repo -- distinct from plain Inside Bar/Mother Bar breakout (already tested
11+ times) via the added edge-position filter on the inside bar itself.

Signal logic
------------
- Trend context: close below its own SMA(trend_window) (source's "short-term
  downtrend"), or trend_window<=0 to disable.
- Bar1/bar2 (today = bar2): inside-day structure (high < bar1's high AND
  low > bar1's low).
- Edge-position filter on bar2 (today): (open-low)/(high-low) <= edge_pct
  AND (high-close)/(high-low) <= edge_pct.
- Entry: NEXT bar's close breaks above the 2-bar pattern's high (max of
  bar1's high, bar2's high).
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
    edge_pct: float = 0.25,
    height_mult: float = 1.0,
    max_hold_days: int = 20,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0,1}-scaled (by leverage_cap) long/flat position series.

    ``leverage_cap`` (default 1.0 = full exposure) scales the binary long
    position down to a fraction of notional -- used to bring crypto MDD
    within threshold without changing the entry/exit trigger logic itself,
    per this repo's established leverage-cap-aware crypto rescue pattern.
    """
    df = _prep(price_df)
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]

    inside_day = (high < high.shift(1)) & (low > low.shift(1))

    rng = (high - low).replace(0, pd.NA)
    open_near_low = (open_ - low) / rng <= edge_pct
    close_near_high = (high - close) / rng <= edge_pct

    if trend_window and trend_window > 0:
        sma = close.rolling(trend_window).mean()
        trend_down = close < sma
    else:
        trend_down = pd.Series(True, index=close.index)

    pattern_confirmed = (
        inside_day & open_near_low & close_near_high & trend_down
    ).fillna(False)

    pattern_high = pd.concat([high, high.shift(1)], axis=1).max(axis=1)
    pattern_low = pd.concat([low, low.shift(1)], axis=1).min(axis=1)
    pattern_height = pattern_high - pattern_low

    breakout_trigger = pattern_confirmed.shift(1).fillna(False) & (close > pattern_high.shift(1))
    height_level = pattern_height.shift(1)
    pattern_high_level = pattern_high.shift(1)

    position = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    entry_idx = 0
    target_level = None
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            hit_target = (target_level is not None) and (close.iloc[i] >= target_level)
            if hit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0.0
                target_level = None
                continue
            position.iloc[i] = leverage_cap
        else:
            if bool(breakout_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                h = height_level.iloc[i]
                base = pattern_high_level.iloc[i]
                target_level = (base + height_mult * h) if pd.notna(h) and pd.notna(base) else None
                position.iloc[i] = leverage_cap
            else:
                position.iloc[i] = 0.0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

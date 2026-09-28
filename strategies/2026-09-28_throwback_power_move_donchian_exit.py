"""Strategy: Donchian breakout entry with a Bulkowski "Throwback Power Move"
defensive exit rule.

Hypothesis (see knowledge_base/strategies_log.jsonl for the id):
Per Bulkowski's Throwbacks page (thepatternsite.com/throwbacks.html, read
2026-09-28 via browser_exec -- web_extract failed, DuckDuckGo backend is
search-only), after an upward breakout ~58% of chart patterns throw back
(return toward the breakout price) within 30 calendar days. The source's own
"Power Move" statistic: when price during the throwback REMAINS AT OR ABOVE
the breakout price, the subsequent rise from breakout to ultimate high
averages 40% (n=400); when price DROPS BELOW the breakout price during the
throwback window, the subsequent rise averages only 29% (n=2,767), and 35%
of those continue falling below the pattern entirely.

This is an EXIT/filter rule layered on a plain N-day Donchian breakout
entry (not itself novel), distinct from this repo's existing
pullback-confirmation ENTRY strategies (which require a pullback before
entering) and from the existing defensive-EXIT overlays (Pipe Top, UTAD,
which trigger on unrelated pattern-completion signals) -- here the exit
condition is specifically "price broke back below its own recent breakout
level within a throwback_window", operationalizing Bulkowski's own
disclosed power-move statistic rather than a generic trend-break stop.

Signal logic
------------
- Entry: close breaks above the rolling `donchian_window`-day high
  (of the prior `donchian_window` bars, no lookahead) -> record breakout
  level = that prior rolling high.
- Throwback-failure exit: within `throwback_window` trading days after
  entry, if close drops back below the breakout level (the "power move"
  failed to hold), exit immediately -- this is the core Bulkowski-derived
  rule (in-window drop below breakout level = lower expected forward
  return, cut losses early rather than waiting for a generic trend break).
- Power-move hold: if the throwback window passes without price dropping
  below the breakout level (i.e. price "remained at or above" it, per the
  source's own criterion for the stronger continuation case), keep the
  position and manage it with a plain trailing stop: exit when close drops
  below the rolling `trail_window`-day low.
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
    donchian_window: int = 20,
    throwback_window: int = 20,
    trail_window: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    rolling_high = high.rolling(donchian_window).max().shift(1)
    rolling_low = low.rolling(trail_window).min().shift(1)

    entry_signal = close > rolling_high

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    breakout_level = None

    for i in range(len(close)):
        c = close.iloc[i]
        if in_position:
            held = i - entry_idx
            # Throwback-failure exit: within the throwback window, price
            # drops back below the breakout level it broke out of.
            if held <= throwback_window and breakout_level is not None and c < breakout_level:
                in_position = False
                position.iloc[i] = 0
                continue
            # Power-move hold: trailing-stop exit once past/through window.
            trail_stop = rolling_low.iloc[i]
            if trail_stop == trail_stop and c < trail_stop:  # not NaN
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]) and rolling_high.iloc[i] == rolling_high.iloc[i]:
                in_position = True
                entry_idx = i
                breakout_level = rolling_high.iloc[i]
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

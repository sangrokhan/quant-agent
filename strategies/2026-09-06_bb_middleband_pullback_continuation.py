"""Strategy: Bollinger middle-band trend-continuation pullback (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl):
Per Money365.Market's Bollinger Bands trend-continuation rule set (quoted
via search snippet, inverted here for the long/uptrend case): "Trend:
Middle band sloping upward. Pullback: Price pulls back down to the middle
band (20-SMA). Entry: Long (or exit short) when price reacts off the
middle band and resumes in the trend direction." This differs from
Bollinger's own "Walking the Bands" trend-continuation strategy already
tested in this repo (2026-09-05-084, accepted -- which stays long WHILE
price hugs the UPPER band and exits on a break below the middle/basis
band) by instead treating a PULLBACK TO the middle band itself as the
entry trigger (buying the dip to the moving average in an established
uptrend), a fundamentally different entry mechanism even though both use
the same three Bollinger lines.

Signal logic (daily bars):
- Uptrend filter: the middle band (basis SMA) itself must have a positive
  slope over `slope_window` bars (per source: "Confirm a sloped middle
  band and clear market structure").
- Pullback: close dips to within `pullback_tolerance` of the middle band
  (from above) after having been in the upper half of the bands.
- Entry: close reacts back upward off the middle band (closes above it
  again after the pullback touch).
- Exit: close breaks below the lower band (trend invalidated) or a
  max_hold_days time-stop.

Source: Money365.Market SERP snippet ("Downtrend Continuation Rules; Trend:
Middle band sloping downward; Rally: Price rallies up to the middle band
(20-SMA); Entry: Short (or exit...)"), inverted for the long/uptrend case
since the source page itself 404'd on direct fetch (read via Google search
result snippet only, per the fallback path when a chosen URL turns out
unreachable -- the fully attributed the exact quoted downtrend rule was
readable in the SERP itself).

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
    bb_window: int = 20,
    bb_std: float = 2.0,
    slope_window: int = 10,
    pullback_tolerance: float = 0.005,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    basis = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    upper = basis + bb_std * std
    lower = basis - bb_std * std

    basis_slope = basis.diff(slope_window)
    uptrend = basis_slope > 0

    near_basis = (close - basis).abs() / basis.replace(0, pd.NA) <= pullback_tolerance
    was_above = close.shift(1) > basis.shift(1)

    touch_and_bounce = near_basis & (close > basis) & was_above.shift(1).fillna(False)
    long_trigger = uptrend & touch_and_bounce

    exit_trigger = close < lower

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(long_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    position.name = "position"
    return position


def generate_returns(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    slope_window: int = 10,
    pullback_tolerance: float = 0.005,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        bb_window=bb_window,
        bb_std=bb_std,
        slope_window=slope_window,
        pullback_tolerance=pullback_tolerance,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns

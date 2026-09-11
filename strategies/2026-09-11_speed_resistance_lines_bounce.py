"""Strategy: Speed Resistance Lines (Edson Gould) 2/3-line bounce, 1/3-line exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-119):
Per StockCharts ChartSchool's "Speed Resistance Lines" article: "Speed
Resistance Lines, sometimes referred to as Speedlines, are trend lines
based on 1/3 and 2/3 retracements... In an uptrend, Speed Resistance Lines
mark two potential support levels to watch. A break below the middle line
[2/3 point] targets a move towards the upper line [1/3 point]. A break
below the lower line [1/3 point] indicates enough weakness to consider a
trend reversal." Speedlines are calculated as: given a swing low and swing
high, the 2/3-point = swing_low + (swing_high - swing_low) * 0.667, and
the 1/3-point = swing_low + (swing_high - swing_low) * 0.333. "These lines
extend to the right as new bars occur" and "it is also possible to redraw
Speed Resistance Lines as new highs form" -- implemented here as a rolling
trailing swing_low/swing_high over a lookback window, recalculated each
bar (rather than a single static anchor pair), which is the mechanical
adaptation needed for a systematic (non-discretionary) backtest.

Mechanical rule implemented:
  - swing_low = rolling min(close, lookback_window); swing_high = rolling
    max(close, lookback_window).
  - two_thirds_line = swing_low + (swing_high-swing_low) * 0.667
  - one_third_line = swing_low + (swing_high-swing_low) * 0.333
  - Uptrend context: swing_high occurs after swing_low in time (i.e. the
    rolling max index > rolling min index within the window -- an actual
    up-move, not a down-move) AND close > SMA(trend_window) (source: only
    meaningful "in an uptrend").
  - Entry (long): close dips below the 2/3 line then bounces back above
    it within confirm_bars ("a break below the middle line targets a move
    towards the upper line" -- we buy the bounce off the 2/3 line testing
    support, betting it holds rather than continuing to the 1/3 line).
  - Exit: close breaks below the 1/3 line ("indicates enough weakness to
    consider a trend reversal"), or a max_hold_days time-stop.

First Speed Resistance Lines strategy in this repo (zero prior hits in
strategies_index.jsonl) -- distinct from Fibonacci retracement (static
0.382/0.5/0.618 ratios, already tested) and Andrews Pitchfork (three-pivot
parallel-tine construction, already tested): Speed Resistance Lines use a
fixed 1/3-2/3 thirds-division of a single high-low swing range, not a
Fibonacci ratio set or a three-point pivot construction.

Source: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/speed-resistance-lines
(read via browser_exec fallback -- web_search DDGS backend errored on
every direct query attempted this cron trigger).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: {0,1})
    generate_returns(price_df, **params) -> pd.Series
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
    lookback_window: int = 60,
    trend_window: int = 100,
    confirm_bars: int = 3,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    swing_low = close.rolling(lookback_window).min()
    swing_high = close.rolling(lookback_window).max()
    swing_range = (swing_high - swing_low).replace(0.0, 1e-12)

    two_thirds = swing_low + swing_range * 0.667
    one_third = swing_low + swing_range * 0.333

    # Determine whether the swing high occurred AFTER the swing low within
    # the window (a genuine up-move, not a down-move).
    def _rolling_argextreme(s: pd.Series, window: int, mode: str) -> pd.Series:
        out = pd.Series(index=s.index, dtype=float)
        vals = s.values
        n = len(vals)
        for i in range(window - 1, n):
            seg = vals[i - window + 1 : i + 1]
            idx = seg.argmin() if mode == "min" else seg.argmax()
            out.iloc[i] = i - window + 1 + idx
        return out

    low_idx = _rolling_argextreme(close, lookback_window, "min")
    high_idx = _rolling_argextreme(close, lookback_window, "max")
    is_uptrend_swing = high_idx > low_idx

    sma = close.rolling(trend_window).mean()
    uptrend_ctx = (close > sma) & is_uptrend_swing.fillna(False)

    below_two_thirds = close < two_thirds
    bounce_confirmed = pd.Series(False, index=close.index)
    for i in range(len(close)):
        if i < confirm_bars:
            continue
        recent_below = below_two_thirds.iloc[max(0, i - confirm_bars) : i].any()
        if recent_below and close.iloc[i] >= two_thirds.iloc[i]:
            bounce_confirmed.iloc[i] = True

    entry = uptrend_ctx.fillna(False) & bounce_confirmed
    exit_weakness = close < one_third

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_weakness.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
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

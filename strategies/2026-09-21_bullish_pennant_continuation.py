"""Strategy: Bullish Pennant continuation breakout, pole-projected target.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-230):
Per QuantifiedStrategies.com's "Pennant Trading Strategy - Explained and
Backtested Insights" (https://www.quantifiedstrategies.com/pennant-trading-strategy/,
read via browser_exec fallback -- web_extract's ddgs backend cannot extract
page content), a bullish pennant is a continuation pattern: (1) a "pole" --
a rapid price ascent; (2) a small triangular consolidation ("pennant",
5-15 bars) with converging highs/lows that follows it, whose low must not
retrace below the pole's own midpoint; (3) a breakout -- price closes above
the pennant's upper boundary, confirming continuation, entered at the next
bar's open. Source's disclosed exit rules: stop-loss below the pennant's
lower boundary; profit target = the pole's own price move projected upward
from the breakout point (measured-move target), with a more conservative
alternative target equal to the pennant's own base size.

The source explicitly states it could not build a "100% quantified"
version itself (relying instead on Bulkowski's qualitative after-the-fact
stats, which show pennants meet their price target only 52-58% of the
time, below Bulkowski's own 80% reliability bar) -- this strategy is this
repo's own numeric operationalization of the source's plain-English rule
descriptions, not a source-disclosed exact backtest, since none exists to
reuse directly.

First "Pennant"/"Flag" chart-pattern entry in this repo (0 prior hits for
either in strategies_index.jsonl) -- distinct from the prior Scallop
(rounded J-shape, no straight trendline convergence) and other breakout
strategies (Donchian/ATR-channel breakouts, which don't require a
preceding "pole" impulse move or a converging-range consolidation shape).

Operationalization:
  - Pole: cumulative log return over pole_window bars (ending
    pole_window+1 bars before the signal bar) >= pole_min_return (the
    "rapid price ascent").
  - Pennant consolidation (pennant_window bars immediately following the
    pole): rolling highs declining and rolling lows rising over the window
    (converging range) -- measured via linear regression slope of the
    window's highs being negative and of the lows being positive (a
    numeric proxy for "converging trendlines" that works for symmetrical,
    ascending, or descending triangles per the source's own description
    that all three sub-shapes count as pennants).
  - Ratio rule: pennant's minimum low over the window >= pole's own
    midpoint (pole_start_price + pole_move/2) -- source's explicit
    "bottom of the flag should not exceed the midpoint of the pole" rule.
  - Breakout: close > pennant window's max high -> entry at NEXT bar's
    open (source's explicit "enter at the open of the next trading day"
    rule).
  - Stop: pennant window's min low (source's disclosed stop reference).
  - Target: entry_price + pole_move * target_pole_mult (source's disclosed
    pole-projection method; target_pole_mult=1.0 reproduces the literal
    rule, allow tuning since Bulkowski's own stats show <80% target
    achievement at the literal 1.0x projection).
  - max_hold_days time-stop fallback if neither stop nor target is hit.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: 1 long/0 flat)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rolling_slope(series: pd.Series, window: int) -> pd.Series:
    x = np.arange(window)
    x_mean = x.mean()
    denom = ((x - x_mean) ** 2).sum()

    def _slope(y: np.ndarray) -> float:
        y_mean = y.mean()
        return float(((x - x_mean) * (y - y_mean)).sum() / denom)

    return series.rolling(window).apply(_slope, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    pole_window: int = 10,
    pole_min_return: float = 0.08,
    pennant_window: int = 10,
    target_pole_mult: float = 1.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {1, 0} long/flat position series."""
    df = _prep(price_df)
    h, l, c = df["high"], df["low"], df["close"]
    o = df["open"]
    n = len(c)

    # Pole: log return over pole_window bars, ending right before the
    # pennant consolidation window starts.
    pole_start_idx = pennant_window + pole_window
    pole_start_price = c.shift(pole_start_idx)
    pole_end_price = c.shift(pennant_window)
    pole_move_pct = (pole_end_price / pole_start_price) - 1.0
    pole_is_rapid = pole_move_pct >= pole_min_return

    # Pennant consolidation: highs declining, lows rising over the window
    # ending at the signal bar (t-1, i.e. shift(1) window of size
    # pennant_window).
    high_slope = _rolling_slope(h, pennant_window).shift(1)
    low_slope = _rolling_slope(l, pennant_window).shift(1)
    converging = (high_slope < 0) & (low_slope > 0)

    pennant_low = l.rolling(pennant_window).min().shift(1)
    pennant_high = h.rolling(pennant_window).max().shift(1)

    pole_midpoint = pole_start_price + (pole_end_price - pole_start_price) / 2.0
    ratio_ok = pennant_low >= pole_midpoint

    breakout = c > pennant_high

    pattern_confirm = (
        pole_is_rapid.fillna(False)
        & converging.fillna(False)
        & ratio_ok.fillna(False)
        & breakout.fillna(False)
    )

    position = pd.Series(0, index=c.index, dtype=int)
    in_position = False
    hold_days_left = 0
    stop_price = None
    target_price = None
    pending_entry_bar = None  # entry happens at NEXT bar's open

    for i in range(n):
        if in_position:
            hit_stop = l.iloc[i] <= stop_price
            hit_target = h.iloc[i] >= target_price
            hold_days_left -= 1
            if hit_stop or hit_target or hold_days_left <= 0:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if pending_entry_bar is not None and i == pending_entry_bar:
            entry_price = o.iloc[i]
            pole_move = pole_move_pct.iloc[pending_entry_bar - 1] * pole_start_price.iloc[pending_entry_bar - 1]
            stop_price = pennant_low.iloc[pending_entry_bar - 1]
            target_price = entry_price + target_pole_mult * pole_move
            if stop_price is not None and pd.notna(stop_price) and stop_price < entry_price:
                in_position = True
                hold_days_left = max_hold_days
                position.iloc[i] = 1
                pending_entry_bar = None
                continue
            pending_entry_bar = None

        if bool(pattern_confirm.iloc[i]) and i + 1 < n:
            pending_entry_bar = i + 1

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

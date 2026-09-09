"""Strategy: Ulcer Index slope (de-stressing) trend-following entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-045):
Per arrowalgo.com's Ulcer Index guide (visited this iteration,
https://arrowalgo.com/ulcer-index-complete-guide-algorithmic-trading/):
the Ulcer Index (UI, Peter Martin 1987, RMS of pct drawdown from the
rolling peak over a lookback window) is a downside-only drawdown-depth-
and-duration metric. The source's own key emphasis is that UI's SLOPE
matters as much as its level: "a falling UI in a rising market means
drawdown stress is clearing -- a positive sign for longs; a rising UI in a
declining market means the drawdown is deepening."

This iteration operationalizes that SLOPE-based signal (distinct from this
repo's prior static-threshold UI strategy, id=2026-09-04-144, which used a
fixed "UI below entry_threshold" level check): long entry when (1) close is
above its own SMA(trend_window) (broad uptrend context) AND (2) the Ulcer
Index has been falling over the past ui_slope_window bars (stress clearing,
i.e. UI.diff(ui_slope_window) < 0). Exit when UI starts rising again
(UI.diff(ui_slope_window) >= 0, stress re-accumulating) or the trend filter
breaks, or a max_hold_days time-stop.

Signal logic
------------
- drawdown_pct[t] = 100 * (rolling_max(close, ui_window)[t] - close[t]) / rolling_max(close, ui_window)[t]
- ulcer_index[t] = sqrt(mean(drawdown_pct[t-ui_window+1:t+1] ** 2))
- ui_slope = ulcer_index.diff(ui_slope_window)  (negative = UI falling = destressing)
- trend_up = close > close.rolling(trend_window).mean()
- Entry (long): trend_up AND ui_slope < 0.
- Exit: ~trend_up OR ui_slope >= 0 OR held >= max_hold_days.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _ulcer_index(close: pd.Series, ui_window: int) -> pd.Series:
    rolling_max = close.rolling(ui_window, min_periods=ui_window).max()
    drawdown_pct = 100.0 * (rolling_max - close) / rolling_max
    ui = drawdown_pct.rolling(ui_window, min_periods=ui_window).apply(
        lambda x: np.sqrt(np.mean(np.square(x))), raw=True
    )
    return ui


def generate_signals(
    price_df: pd.DataFrame,
    ui_window: int = 14,
    ui_slope_window: int = 5,
    trend_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ui = _ulcer_index(close, ui_window)
    ui_slope = ui.diff(ui_slope_window)

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    destressing = ui_slope < 0
    entry = trend_up.fillna(False) & destressing.fillna(False)
    exit_condition = (~trend_up.fillna(False)) | (ui_slope >= 0).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_condition.iloc[i]) or held >= max_hold_days:
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

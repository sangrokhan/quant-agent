"""Strategy: Ulcer Index drawdown-risk regime gate on an SMA trend-following
entry (long only).

Hypothesis (knowledge_base id TBD, this cron trigger):
Per StockCharts ChartSchool's Ulcer Index page
(https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ulcer-index):
the Ulcer Index (Peter Martin & Byron McCann, 1987) = sqrt(mean(squared pct
drawdowns from the rolling N-period high)) -- a downside-only volatility
measure that "hovers near zero when prices regularly record higher highs
and advance" and "rises when prices move lower and extend from their
recent high." The source doesn't give an explicit trading rule (it frames
UI purely as a risk-measurement tool for the Ulcer Performance
Index/Martin Ratio), so this iteration operationalizes it as a regime gate
in this repo's established vol-forecast-gate pattern (cf. accepted HAR-D
2026-09-20-100, which gated on a variance forecast rather than a
drawdown-depth measure): only stay long in an SMA-confirmed uptrend WHILE
the Ulcer Index is at or below its own trailing percentile threshold
(i.e. current drawdown depth/duration is not unusually severe relative to
its own recent history); exit when UI spikes above that threshold (a
"stomach ulcer" event per Martin's own framing) or the trend breaks. First
Ulcer Index entry in this repo (0 prior KB hits) -- distinct from every
existing ATR/realized-vol/HAR-D volatility gate here because UI is
specifically a squared-drawdown-depth measure (asymmetric, drawdown-only),
not a symmetric return-variance measure.

Signal logic (long side only)
------------------------------
- Ulcer Index (UI): over a rolling `ui_window`, pct drawdown from the
  running max close within that window at each bar, UI_t =
  sqrt(mean(drawdown_pct**2)) over the window.
- Regime gate: UI's own trailing `ui_percentile_window`-bar percentile rank
  <= `ui_gate_percentile` (e.g. 0.5 = UI is at or below its own median --
  "typical" or better drawdown risk, not currently elevated).
- Entry: close > SMA(trend_window) (uptrend) AND UI regime gate is TRUE.
- Exit: UI regime gate turns FALSE (drawdown risk elevated beyond the
  gate threshold), OR trend breaks (close <= SMA(trend_window)), OR
  `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def _ulcer_index(close: pd.Series, window: int) -> pd.Series:
    running_max = close.rolling(window, min_periods=window).max()
    drawdown_pct = 100.0 * (close - running_max) / running_max
    sq = drawdown_pct ** 2
    ui = sq.rolling(window, min_periods=window).mean() ** 0.5
    return ui


def generate_signals(
    price_df: pd.DataFrame,
    ui_window: int = 14,
    ui_percentile_window: int = 252,
    ui_gate_percentile: float = 0.5,
    trend_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    ui = _ulcer_index(close, ui_window)
    ui_rank = ui.rolling(ui_percentile_window, min_periods=ui_percentile_window).apply(
        lambda x: (x <= x.iloc[-1]).mean(), raw=False
    )
    gate_ok = (ui_rank <= ui_gate_percentile).fillna(False)

    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        eligible = bool(uptrend.iloc[i]) and bool(gate_ok.iloc[i])
        if in_position:
            held = i - entry_idx
            if (not eligible) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if eligible:
            in_position = True
            entry_idx = i
            position.iloc[i] = 1
            continue

        position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, leverage_cap: float = 1.0, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret * leverage_cap
    return strategy_ret

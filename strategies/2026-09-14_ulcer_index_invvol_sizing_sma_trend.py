"""Strategy: SMA(trend_window) directional gate with continuous Ulcer Index
INVERSE-VOLATILITY (downside-risk) conditioning multiplier + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Ulcer Index (Peter Martin & Byron McCann, 1987/1989): percent-drawdown from
the rolling N-period max close, squared, averaged, then square-rooted --
UI = sqrt(mean((100*(Close - RollingMaxClose)/RollingMaxClose)^2)). Formula
confirmed via StockCharts ChartSchool (browser_exec after web_extract
DuckDuckGo-backend failure). This repo has 3 prior Ulcer Index entries
(2026-09-04-144 low-UI-level long entry gate, 2026-09-09/10 UI-slope
trend-following filters), ALL using UI as a BINARY threshold/slope GATE for
a separate entry trigger. None used UI's own continuous magnitude as an
INVERSE-VOLATILITY sizing dial. This iteration follows the BBW/GAPO
inverse-vol-conditioning pattern already validated twice this cron trigger:
rolling min-max normalize UI, INVERT it (low UI = shallow/brief drawdowns =
calm uptrend -> scale exposure UP; high UI = deep/prolonged drawdown pain =
scale exposure DOWN), applied within an SMA(trend_window) uptrend gate.
First Ulcer Index continuous-sizing / inverse-volatility-conditioning
variant in this repo.

Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ulcer-index
(fetched via browser_exec this iteration).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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
    """UI = sqrt(mean(pct_drawdown_from_rolling_max^2)) over ui_window."""
    rolling_max = close.rolling(ui_window, min_periods=1).max()
    pct_drawdown = (close - rolling_max) / rolling_max.replace(0.0, np.nan) * 100.0
    squared_avg = (pct_drawdown ** 2).rolling(ui_window).mean()
    ui = np.sqrt(squared_avg)
    return ui


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ui_window: int = 14,
    norm_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Ulcer Index is rolling min-max normalized to [0,1] over `norm_window`
    bars, then INVERTED (1 - normalized) and rescaled to [-1,+1] so calm
    (low drawdown-pain) regimes scale exposure UP.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    ui = _ulcer_index(close, ui_window)
    roll_min = ui.rolling(norm_window).min()
    roll_max = ui.rolling(norm_window).max()
    span = (roll_max - roll_min).replace(0.0, np.nan)
    normalized = (ui - roll_min) / span
    inverted_centered = (1.0 - normalized.fillna(0.5)) * 2.0 - 1.0  # [0,1] -> invert -> [-1,1]
    dial = inverted_centered.clip(-1.0, 1.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ui_window: int = 14,
    norm_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        ui_window=ui_window,
        norm_window=norm_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

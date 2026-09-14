"""Strategy: SMA(trend_window) directional gate with continuous Pring's
Special K sizing overlay + deadband, leverage-cap-aware for crypto from the
start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Pring's Special K: weighted sum of 12 SMA-smoothed ROC legs spanning
10-530-period lookbacks (Martin Pring's four-year-business-cycle
composite), per https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/prings-special-k
(visited this iteration) and LuxAlgo/TradingView search-snippet formula:
SpecialK = SMA(ROC(10),10)*1 + SMA(ROC(15),10)*2 + SMA(ROC(20),10)*3 +
SMA(ROC(30),15)*4 + SMA(ROC(40),50)*1 + SMA(ROC(65),65)*2 +
SMA(ROC(75),75)*3 + SMA(ROC(100),100)*4 + SMA(ROC(195),130)*1 +
SMA(ROC(265),130)*2 + SMA(ROC(390),130)*3 + SMA(ROC(530),195)*4. This repo
has 1 prior Special K entry (2026-09-06-107), a binary
Special-K-vs-100-period-SMA-signal-line crossover, rejected as a near-miss
(QQQ/SPY Sharpe 0.79-0.82, just under 1.0 threshold, all other validators
passed). This iteration reframes Special K's own continuous magnitude
(already a momentum composite, roughly zero-centered by construction since
each leg is an SMA-smoothed ROC) as a CONTINUOUS SIZING dial: rolling
z-scored + tanh-squashed to [-1,1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate, deadband to cut turnover, leverage_cap for
crypto. First Special K continuous-sizing variant -- follows this cron
trigger's repeatedly-validated pattern of reframing an already-confirmed
binary-crossover-near-miss indicator's magnitude as a sizing dial instead.

Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/prings-special-k
(visited this iteration, browser_exec fallback -- previous web_search
attempts this iteration also failed with DDGS "No results found"); formula
also reuses repo's own already-confirmed 12-leg coefficient table from
strategies/2026-09-06_special_k_signal_crossover.py.

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


# Canonical Pring Special K legs: (roc_period, sma_window, weight)
_SPECIAL_K_LEGS = [
    (10, 10, 1),
    (15, 10, 2),
    (20, 10, 3),
    (30, 15, 4),
    (40, 50, 1),
    (65, 65, 2),
    (75, 75, 3),
    (100, 100, 4),
    (195, 130, 1),
    (265, 130, 2),
    (390, 130, 3),
    (530, 195, 4),
]


def _special_k(close: pd.Series) -> pd.Series:
    total = pd.Series(0.0, index=close.index)
    for roc_period, sma_window, weight in _SPECIAL_K_LEGS:
        roc = close.pct_change(roc_period) * 100.0
        smoothed = roc.rolling(sma_window, min_periods=sma_window).mean()
        total = total.add(smoothed.fillna(0.0) * weight, fill_value=0.0)
    return total


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
    zscore_window: int = 150,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Special K's own composite momentum is rolling z-scored over
    `zscore_window` bars and tanh-squashed to [-1,+1] before use as a
    sizing dial. `zscore_window` defaults to 150 (rather than the repo's
    usual 100) since Special K's longest leg (530-period ROC) needs a
    longer warm-up before its z-score is meaningful.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    special_k = _special_k(close)

    roll_mean = special_k.rolling(zscore_window).mean()
    roll_std = special_k.rolling(zscore_window).std()
    zscore = (special_k - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    zscore_window: int = 150,
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
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

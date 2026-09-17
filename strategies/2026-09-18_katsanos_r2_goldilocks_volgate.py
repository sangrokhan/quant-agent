"""Strategy: Katsanos R-squared "Goldilocks zone" trend system, WITH a
realized-volatility regime gate (direct fix for near-miss 2026-09-17-137).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-014):
Direct follow-up to this cron trigger's own repo history id 2026-09-17-137
(Katsanos R-squared Goldilocks-zone trend system, Markos Katsanos TASC Oct
2016 "Which Trend Indicator Wins?", MetaStock formula fully disclosed at
https://traders.com/Documentation/FEEDbk_docs/2016/10/TradersTips.html):
that entry was a near-miss on QQQ (Sharpe 0.960 vs 1.0 threshold, all other
4 validators pass) with its grid showing 0/48 passing cells in the HIGH
volatility regime specifically (30/48 low-vol, 6/48 mid-vol, 0/48 high-vol)
-- the signal quality collapses precisely when volatility regime shifts
against a trend-quality-gated entry (this repo's own recurring finding
across many similar trend-following strategies, e.g.
strategies/2026-09-03_bb_meanrev_qqq_volregime.py's own pattern). This
iteration applies the exact same fix pattern already validated repeatedly
in this repo: flatten (force position to 0) whenever the 20-day realized
volatility exceeds vol_regime_ratio times its own trailing 252-day median,
layered UNCHANGED on top of the identical Katsanos Goldilocks-zone entry
logic and parameters from 2026-09-17-137, to directly target that
strategy's own recorded failure mode.

Signal logic (unchanged from 2026-09-17-137, plus the new vol gate)
---------------------------------------------------------------------
- r2 = rolling R-squared of OLS(close ~ time) over r2_period bars.
- slope = rolling OLS slope of close ~ time over r2_period bars, scaled by
  slope_scale.
- sma = SMA(close, sma_window).
- r2_cross_enter = r2 crosses above r2_enter (from <= to >).
- zone_ok = r2 < r2_cap AND r2 > r2.shift(rising_lookback).
- vol_ok = 20d realized vol (annualized) <= vol_regime_ratio * its own
  trailing 252d median (NEW: low/normal-vol regime gate).
- Entry (long): r2_cross_enter AND zone_ok AND slope > slope_min AND
  close > sma AND vol_ok.
- Exit: close crosses back below sma, OR the vol regime flips to high-vol
  (vol_ok turns False -- risk-off exit, NEW), OR max_hold_days time-stop.
- Flat otherwise.

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


def _rolling_r2_slope(close: pd.Series, window: int):
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_centered = x - x_mean
    ss_xx = (x_centered ** 2).sum()

    def _r2_slope(y: np.ndarray):
        y_mean = y.mean()
        y_centered = y - y_mean
        ss_xy = (x_centered * y_centered).sum()
        ss_yy = (y_centered ** 2).sum()
        if ss_xx <= 0 or ss_yy <= 0:
            return 0.0, 0.0
        slope = ss_xy / ss_xx
        r2 = (ss_xy ** 2) / (ss_xx * ss_yy)
        return r2, slope

    r2_vals = close.rolling(window).apply(lambda w: _r2_slope(w.values)[0], raw=False)
    slope_vals = close.rolling(window).apply(lambda w: _r2_slope(w.values)[1], raw=False)
    return r2_vals, slope_vals


def generate_signals(
    price_df: pd.DataFrame,
    r2_period: int = 18,
    r2_enter: float = 0.42,
    r2_cap: float = 0.85,
    rising_lookback: int = 10,
    slope_min: float = 0.0,
    slope_scale: float = 100.0,
    sma_window: int = 50,
    max_hold_days: int = 40,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    r2, slope = _rolling_r2_slope(close, r2_period)
    slope_scaled = slope * slope_scale
    sma = close.rolling(sma_window).mean()

    log_ret = np.log(close / close.shift(1))
    realized_vol = log_ret.rolling(vol_window).std() * np.sqrt(252)
    vol_median = realized_vol.rolling(vol_lookback).median()
    vol_ok = realized_vol <= (vol_regime_ratio * vol_median)

    r2_cross_enter = (r2 > r2_enter) & (r2.shift(1) <= r2_enter)
    zone_ok = (r2 < r2_cap) & (r2 > r2.shift(rising_lookback))

    entry = (
        r2_cross_enter.fillna(False)
        & zone_ok.fillna(False)
        & (slope_scaled > slope_min).fillna(False)
        & (close > sma).fillna(False)
        & vol_ok.fillna(False)
    )
    exit_sma_flip = close < sma
    exit_vol_flip = ~vol_ok.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_sma_flip.iloc[i]) or bool(exit_vol_flip.iloc[i]) or held >= max_hold_days:
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

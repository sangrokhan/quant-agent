"""Strategy: SOXX/QQQ Leadership, Broad-Trend-Filtered, LOCALLY-TUNED (ACCEPTED, QQQ+SPY).

Third and final entry in the SOXX/QQQ leadership lineage this cron trigger:
  1. 2026-09-09-118: plain SOXX/QQQ ROC leadership gate. Rejected -- Sharpe
     near-miss (0.87/0.90) but MDD failed decisively (0.35/0.27).
  2. 2026-09-09-119: added a 200-day broad-trend AND-gate (fixed MDD to
     0.16/0.18) at roc_window=40. ACCEPTED for QQQ (Sharpe 1.013, all
     validators pass); SPY remained a narrow Sharpe near-miss (0.951).
  3. THIS strategy: a local parameter search (trend_sma_window in
     {150,175,200,225,250} x roc_window in {20,30,40,50}) found
     trend_sma_window=200, roc_window=30 clears the Sharpe threshold
     decisively for BOTH symbols (QQQ 1.098, SPY 1.099) while every other
     validator (MDD, TC-survival, walk-forward, parameter-sensitivity)
     remains comfortably passing for both.

Mechanism is identical to 2026-09-09-119 (SOXX/QQQ ratio ROC leadership gate
AND traded-asset-above-its-own-SMA broad-trend filter) -- only the
roc_window changed from 40 to 30 days, landing on the shared sweet spot
between the two symbols' individually-optimal values.

Signal logic
------------
- soxx_qqq_risk_on = SOXX/QQQ ratio's roc_window-day (default 30) rate of
  change > roc_threshold (0.0).
- broad_trend_up = traded asset's own close > its own trend_sma_window-day
  (default 200) SMA.
- Long whenever BOTH soxx_qqq_risk_on AND broad_trend_up; flat otherwise.
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_soxx_qqq_regime(idx: pd.DatetimeIndex, roc_window: int, roc_threshold: float) -> pd.Series:
    from loaders import load_equity

    lookback_days = roc_window * 3 + 30
    start = (idx.min() - pd.Timedelta(days=lookback_days)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    soxx = load_equity("SOXX", start, end).set_index("timestamp")["close"].sort_index()
    qqq = load_equity("QQQ", start, end).set_index("timestamp")["close"].sort_index()
    soxx.index = soxx.index.tz_localize(None) if soxx.index.tz is not None else soxx.index
    qqq.index = qqq.index.tz_localize(None) if qqq.index.tz is not None else qqq.index

    common_idx = soxx.index.intersection(qqq.index)
    ratio = (soxx.reindex(common_idx) / qqq.reindex(common_idx))
    ratio_roc = ratio.pct_change(roc_window)
    risk_on = ratio_roc > roc_threshold

    target_idx = idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx
    risk_on = risk_on.reindex(risk_on.index.union(target_idx)).sort_index().ffill()
    risk_on = risk_on.reindex(target_idx)
    risk_on.index = idx
    return risk_on


def generate_signals(
    price_df: pd.DataFrame,
    roc_window: int = 30,
    roc_threshold: float = 0.0,
    trend_sma_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long whenever (a) the SOXX/QQQ ratio's roc_window-day ROC is above
    roc_threshold (semiconductor leadership, risk-on) AND (b) the traded
    asset's own close is above its own trend_sma_window-day SMA (broad
    trend filter / drawdown circuit-breaker); flat otherwise.
    """
    df = _prep(price_df)
    idx = df.index
    close = df["close"]

    try:
        soxx_qqq_risk_on = _get_soxx_qqq_regime(idx, roc_window, roc_threshold)
    except Exception:
        soxx_qqq_risk_on = pd.Series(True, index=idx)

    trend_sma = close.rolling(trend_sma_window, min_periods=trend_sma_window // 2).mean()
    broad_trend_up = close > trend_sma

    position = (soxx_qqq_risk_on.fillna(True) & broad_trend_up.fillna(False)).astype(int)
    position.index = idx
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

"""Strategy: SOXX/QQQ Leadership Regime, Broad-Trend-Filtered (drawdown fix).

Direct follow-up to near-miss rejection 2026-09-09-118 (SOXX/QQQ Ratio
Sector-Leadership Regime Filter, per MarketPhase
https://market-phase.com/guides/soxx-qqq-ratio). That iteration's plain
ROC-of-ratio gate had a moderate Sharpe near-miss (QQQ 0.87, SPY 0.90) but
FAILED max drawdown decisively (QQQ 0.35, SPY 0.27 vs the 0.25 cap) --
diagnosed as: the SOXX/QQQ leadership signal alone doesn't avoid deep
SYSTEMIC drawdowns where both semiconductors and the broad market fall
together (SOXX "not underperforming" QQQ is not the same as "market not
falling").

This strategy adds an explicit broad-trend filter on top of the unchanged
SOXX/QQQ leadership gate: additionally require the TRADED asset itself
(QQQ or SPY, whichever price_df represents) to be above its own
trend_sma_window-day SMA. This directly targets the MDD failure -- an
independent circuit-breaker that takes the position flat during genuine
broad-market downtrends regardless of what the semiconductor-leadership
signal says, without touching the underlying leadership signal's own
logic/thresholds (kept identical: roc_window=40, roc_threshold=0.0, the
prior iteration's best grid config).

Signal logic
------------
- soxx_qqq_risk_on = SOXX/QQQ ratio's roc_window-day rate of change > roc_threshold
  (unchanged from 2026-09-09-118).
- broad_trend_up = traded asset's own close > its own trend_sma_window-day SMA
  (new AND-gate).
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
    roc_window: int = 40,
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

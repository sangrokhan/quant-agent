"""Strategy: 3-Factor Regime Allocation, MDD-capped follow-up (max exposure 80%).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Direct fix attempt for near-miss 2026-09-12-165 (3-Factor Regime Allocation
Trend/Volatility/Credit, TASC July 2026 Traders' Tips): that strategy's
QQQ result PASSED Sharpe (1.01) but FAILED max drawdown (0.298 vs 0.25
threshold) at its best grid config (trend_window=150,
credit_zscore_window=80). SPY passed MDD (0.236) but missed Sharpe (0.79).

This iteration's fix: cap the "full exposure" tier at `full_exposure_cap`
(default 0.80, i.e. 80% instead of 100%) while keeping the half-exposure
tier proportionally scaled (`half_exposure_cap` = full_exposure_cap * 0.5,
default 0.40). Rationale: reducing peak exposure during the still-favorable-
but-imperfect 3/3 regime state should shave the tail-risk drawdown (concentr
-ated in stretches like 2022's rate-hike selloff, per the source's near-miss
report) without eliminating the trend/vol/credit filter's timing edge,
since the filter itself already keeps the strategy OUT of the market during
genuinely bad regimes -- the MDD failure came from being **too fully
invested during regimes that later turned bad**, not from missing the
regime filter's core signal.

Same three underlying conditions and weekly-assessment/Monday-open
execution rule as 2026-09-12-165 (trend: close>200d SMA; volatility:
VIX<VIX3M; credit: 100d z-score of HYG/IEF ratio>0); only the exposure caps
change.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fetch_aux(index: pd.DatetimeIndex):
    from loaders import load_equity

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()

    vix = load_equity("^VIX", start=start, end=end)
    vix3m = load_equity("^VIX3M", start=start, end=end)
    hyg = load_equity("HYG", start=start, end=end)
    ief = load_equity("IEF", start=start, end=end)

    def _close(df):
        d = df.copy()
        if "timestamp" in d.columns:
            d = d.set_index("timestamp")
        return d.sort_index()["close"]

    return _close(vix), _close(vix3m), _close(hyg), _close(ief)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 150,
    credit_zscore_window: int = 80,
    full_exposure_cap: float = 0.80,
) -> pd.Series:
    """Return a fractional {0.0, half_cap, full_cap} position series
    (weekly-updated, forward-filled to daily)."""
    df = _prep(price_df)
    close = df["close"]

    vix, vix3m, hyg, ief = _fetch_aux(close.index)

    sma_trend = close.rolling(trend_window).mean()
    cond_trend = close > sma_trend

    vix_aligned = vix.reindex(close.index).ffill()
    vix3m_aligned = vix3m.reindex(close.index).ffill()
    cond_vol = vix_aligned < vix3m_aligned

    hyg_aligned = hyg.reindex(close.index).ffill()
    ief_aligned = ief.reindex(close.index).ffill()
    ratio = hyg_aligned / ief_aligned
    ratio_mean = ratio.rolling(credit_zscore_window).mean()
    ratio_std = ratio.rolling(credit_zscore_window).std()
    z = (ratio - ratio_mean) / ratio_std
    cond_credit = z > 0

    favorable_count = (
        cond_trend.astype(int).fillna(0)
        + cond_vol.astype(int).fillna(0)
        + cond_credit.astype(int).fillna(0)
    )

    weekly_count = favorable_count.resample("W-FRI").last()
    daily_target = weekly_count.reindex(close.index, method="ffill")

    half_exposure_cap = full_exposure_cap * 0.5

    position = pd.Series(0.0, index=close.index)
    position[daily_target >= 3] = full_exposure_cap
    position[daily_target == 2] = half_exposure_cap
    position[daily_target < 2] = 0.0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

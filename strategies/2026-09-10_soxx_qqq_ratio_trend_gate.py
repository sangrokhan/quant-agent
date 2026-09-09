"""Strategy: SOXX/QQQ ratio momentum regime gate on QQQ/SPY/BTC/ETH SMA trend.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-044):
Per market-phase.com's SOXX/QQQ Ratio guide (visited this iteration,
https://market-phase.com/guides/soxx-qqq-ratio): semiconductors sit
unusually far upstream in the economy (long order lead times, "double
ordering" effect), so SOXX outperforming QQQ (rising SOXX/QQQ ratio) is a
leading indicator of rising risk appetite, while SOXX underperforming QQQ
(falling ratio) is an early warning of risk-off rotation into safer
mega-caps -- often before the broader market turns. Source's own scoring
approach: look at the ratio's 4-week (20 trading day) rate of change
relative to a longer-term baseline.

This iteration operationalizes that as a regime gate on top of this repo's
already-validated cross-asset ratio-trend regime-gate construction (same
pattern as the accepted 2026-09-10-041 yield-curve+SMA and other prior
ratio-gated trend strategies): long only when (1) close > SMA(trend_window)
(broad trend-following signal) AND (2) the SOXX/QQQ ratio's own
roc_window-day rate of change is positive (semiconductors currently
outperforming, i.e. rising risk appetite per the source's own leading-
indicator thesis). Applied to QQQ/SPY (the ratio's natural equity domain)
and, as a cross-asset-class test, to BTC/ETH (crypto has no semiconductor-
sector analogue, but a tech-sector-leadership macro signal may still carry
information about broad risk appetite that spills into crypto). First
SOXX/QQQ-ratio-based strategy in this repo (distinct from other intra-tech
ratio gates like RSP/SPY breadth 2026-09-10-040, Copper/Gold 2026-09-10-039,
Growth/Value 2026-09-05-068, and beta-rotation XLU/SPY 2026-09-05-067).

Signal logic
------------
- soxx_qqq_ratio = SOXX.close / QQQ.close (equity data; supplied externally
  as a pd.DataFrame with a `ratio` column, pre-aligned by the caller).
- ratio_roc = soxx_qqq_ratio.pct_change(roc_window) (source's "4-week rate
  of change", default roc_window=20 trading days).
- risk_on = ratio_roc > 0.
- Trend signal: close > close.rolling(trend_window).mean().
- Position: long only when trend signal AND risk_on both true; flat
  otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both require a `ratio_df` kwarg: a pd.DataFrame with a DatetimeIndex and a
`ratio` column (SOXX/QQQ), pre-aligned to price_df's asset by the caller/
grid harness.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _risk_on(index: pd.DatetimeIndex, ratio_df: pd.DataFrame, roc_window: int) -> pd.Series:
    rdf = ratio_df.copy()
    target_index = index
    if getattr(target_index, "tz", None) is not None:
        target_index = target_index.tz_localize(None)
    if getattr(rdf.index, "tz", None) is not None:
        rdf.index = rdf.index.tz_localize(None)

    ratio = rdf["ratio"].sort_index()
    ratio_roc = ratio.pct_change(roc_window)
    risk_on = ratio_roc > 0
    risk_on_aligned = risk_on.reindex(target_index.union(risk_on.index)).sort_index().ffill().reindex(target_index)
    risk_on_aligned.index = index
    return risk_on_aligned.fillna(False).astype(bool)


def generate_signals(
    price_df: pd.DataFrame,
    ratio_df: pd.DataFrame,
    trend_window: int = 50,
    roc_window: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    risk_on = _risk_on(df.index, ratio_df, roc_window)

    position = (trend_up.fillna(False) & risk_on).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

"""Strategy: SMA trend-following on the primary asset, gated by the ROLLING
PEARSON CORRELATION between the primary asset and TLT (20+ Year Treasury
ETF) as a regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://www.quantifiedstrategies.com/correlation-trading-strategies/
("Index and Bond ETF Correlation Rotation" section): the source describes a
regime table where a 90-day rolling SPY-TLT correlation below -0.4 is
"normal diversification" (bonds hedge equity drawdowns), -0.4 to +0.3 is
"transitional", and above +0.3 means "both moving together" (bonds lose
their hedging benefit, historically coinciding with inflation/rate-driven
stress episodes like 2022). This strategy operationalizes the qualitative
regime distinction as a binary gate on a trend-following signal: participate
in a trend-following long only when the rolling correlation is BELOW a
threshold (the "normal"/negative-correlation regime, when equities have
historically performed better and bonds provide a real diversification
backstop); go flat when correlation rises above the threshold (the
2022-style "everything moves together" regime).

This is a structurally new signal for this repo: prior SPY/TLT-adjacent
entries (2026-09-05-036) used a PRICE-RATIO SMA crossover, not a rolling
PEARSON CORRELATION OF RETURNS regime gate -- a materially different
statistic (ratio trend vs. co-movement of returns).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} participation)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, causal -- correlation/trend computed only from data known
        as of the prior close, shifted by 1 before use)
"""

from __future__ import annotations

import pandas as pd

from loaders import load_equity


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _tlt_close_aligned(index: pd.DatetimeIndex) -> pd.Series:
    """Fetch TLT daily close and align to the given index (equity trading
    calendar). Falls back to forward-fill for any missing bars."""
    start = index.min()
    end = index.max()
    tlt_df = load_equity("TLT", start.to_pydatetime(), end.to_pydatetime())
    tlt_df = _prep(tlt_df)
    tlt_close = tlt_df["close"].reindex(index).ffill()
    return tlt_close


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    corr_window: int = 90,
    corr_threshold: float = 0.3,
) -> pd.Series:
    """Return a {0,1} participation series: 1 = long trend-following
    position, 0 = flat.

    Trend condition: close > SMA(trend_window).
    Regime gate: rolling `corr_window`-day Pearson correlation between the
    primary asset's daily returns and TLT's daily returns must be BELOW
    `corr_threshold` (i.e. NOT in the "everything moves together" regime).
    Both conditions use only information known as of the PRIOR close
    (shifted by 1) to avoid look-ahead.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_sma = close.rolling(trend_window).mean()
    above_trend = (close > trend_sma).fillna(False)

    tlt_close = _tlt_close_aligned(close.index)
    asset_ret = close.pct_change()
    tlt_ret = tlt_close.pct_change()
    rolling_corr = asset_ret.rolling(corr_window).corr(tlt_ret)
    calm_regime = (rolling_corr < corr_threshold).fillna(False)

    raw_signal = (above_trend & calm_regime).astype(int)
    # Shift by 1: today's participation decision uses yesterday's known
    # trend/correlation state.
    position = raw_signal.shift(1).fillna(0).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Daily close-to-close strategy returns: position[t] * (close[t]/close[t-1] - 1)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = (position * daily_ret).fillna(0.0)
    strat_returns.name = "strategy_returns"
    return strat_returns

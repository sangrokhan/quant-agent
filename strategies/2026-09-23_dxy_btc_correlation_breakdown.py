"""Strategy: DXY-BTC rolling correlation breakdown regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per SERP snippets from a TradingView "Correlations" indicator description
("2. Correlation Breakdown Detection: Short-term correlation (35 bars) is
compared against long-term correlation (100 bars)") and Matrixport BIT
Knowledge Hub's risk-management framing ("The DXY-Bitcoin inverse
correlation has historically been strongest in moderate environments. In
acute dollar [stress], correlation breakdown [occurs]"), visited this
iteration -- the idea is that the well-known DXY/BTC INVERSE correlation is
not stable: it holds in "moderate" (calm) macro regimes and breaks down
(becomes weaker/less negative, or flips positive) during acute dollar
stress or crypto-specific idiosyncratic events.

This repo already tested three DXY angles: absolute level vs its own 50-day
SMA (2026-09-05-026, accepted equity), DXY rate-of-change momentum
(2026-09-09-113, rejected), and DXY two-level absolute hysteresis
(2026-09-20-026). None of them used the ROLLING CORRELATION BETWEEN DXY and
the traded asset itself as the regime signal -- this strategy is the first
to do so, and applies specifically to crypto (BTC/USDT), which is the asset
class the sources describe as most exposed to acute DXY-driven stress
episodes.

Mechanism: compute rolling Pearson correlation of BTC's daily returns vs
DXY's daily returns over a short window (`short_window`, default 35 per the
TradingView source's own default) and a long window (`long_window`, default
100, also per source). When SHORT-window correlation becomes MORE NEGATIVE
than the LONG-window correlation (i.e. short_corr < long_corr - a buffer),
that signals the inverse relationship is currently STRONGER than its own
longer-run baseline -- per the Matrixport framing, this is the "moderate
environment" where the inverse relationship is intact and reliable, so the
strategy treats it as a confirmation to trade a simple SMA trend-following
signal on BTC. When short-window correlation is NOT more negative than the
long-window baseline (i.e. the inverse relationship has weakened/broken
down, matching the sources' "acute stress" / decoupling description), the
strategy goes flat, since the DXY-based macro read is considered unreliable
in that regime.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import sys
import os
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_dxy_returns(idx: pd.DatetimeIndex) -> pd.Series:
    """Fetch DXY daily returns and reindex/ffill onto the target index."""
    from loaders import load_equity

    start = idx.min() - pd.Timedelta(days=200)
    end = idx.max() + pd.Timedelta(days=2)
    dxy_df = load_equity("DX-Y.NYB", start.to_pydatetime(), end.to_pydatetime())
    dxy_df = _prep(dxy_df)
    dxy_close = dxy_df["close"]
    dxy_returns = dxy_close.pct_change()

    # DXY is a daily (business-day) series; the traded asset (esp. crypto)
    # may be on a different (e.g. hourly) index. Reindex onto normalized
    # dates first, then map back.
    dxy_by_date = dxy_returns.copy()
    dxy_by_date.index = dxy_by_date.index.normalize()
    dxy_by_date = dxy_by_date[~dxy_by_date.index.duplicated(keep="last")]

    target_dates = idx.normalize()
    aligned = dxy_by_date.reindex(target_dates).ffill()
    aligned.index = idx
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    short_window: int = 35,
    long_window: int = 100,
    buffer: float = 0.05,
    trend_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long whenever BOTH:
      (a) close > SMA(trend_window) (simple uptrend confirmation), AND
      (b) rolling short_window-bar Pearson correlation of asset-returns vs
          DXY-returns is MORE NEGATIVE than the rolling long_window-bar
          correlation minus `buffer` (the inverse DXY relationship is
          currently stronger than its own longer-run baseline -- the
          "moderate/reliable" regime per source).
    Flat otherwise (including whenever the correlation-breakdown condition
    is not met, i.e. the DXY relationship has weakened or reversed).
    """
    df = _prep(price_df)
    close = df["close"]

    asset_returns = close.pct_change()
    dxy_returns = _get_dxy_returns(df.index)

    short_corr = asset_returns.rolling(short_window).corr(dxy_returns)
    long_corr = asset_returns.rolling(long_window).corr(dxy_returns)

    corr_breakdown_ok = short_corr < (long_corr - buffer)

    sma = close.rolling(trend_window).mean()
    trend_ok = close > sma

    position = (corr_breakdown_ok.fillna(False) & trend_ok.fillna(False)).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    short_window: int = 35,
    long_window: int = 100,
    buffer: float = 0.05,
    trend_window: int = 50,
) -> pd.Series:
    """Daily strategy returns: position(t-1) * price_return(t) (no lookahead)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        short_window=short_window,
        long_window=long_window,
        buffer=buffer,
        trend_window=trend_window,
    )
    price_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(float) * price_returns
    return strat_returns

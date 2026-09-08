"""Strategy: Intra-Basket Correlation-Ratio Regime Filter for Trend-Following.

Hypothesis (see knowledge_base/strategies_log.jsonl, this id), sourced from
Quantpedia "Refining ETF Asset Momentum Strategy"
(https://quantpedia.com/refining-etf-asset-momentum-strategy/, referencing
the underlying "How to Improve Commodity Momentum Using Intra-Market
Correlation" research): momentum/trend-following strategies work best when
short-term (20-day) average pairwise correlation among a diverse basket of
assets EXCEEDS long-term (250-day) average pairwise correlation -- i.e. when
correlations are currently elevated relative to their own history, momentum
persists; when short-term correlation is comparatively LOW (correlations
loosening), reversal/mean-reversion dominates and trend signals should be
switched off. The source used this correlation ratio to gate a
multi-asset long-short ETF momentum book; here we adapt it as a single-asset
regime GATE on top of a simple SMA trend-following signal: stay long the
primary asset only while (a) price is above its own SMA(trend_window)
*and* (b) the basket's rolling 20d/250d average-pairwise-correlation ratio
is >= corr_ratio_threshold (favorable-for-momentum regime); go flat
otherwise (either downtrend, or a correlation regime where trend signals
are known from the source to underperform).

This differs from prior correlation-based entries in this repo: the CTI
dual-period crossover (2026-09-08-033) uses price-vs-ideal-trend
correlation on a SINGLE asset, the V/MA and BTC/GLD pairs entries
(2026-09-08-074/082) use pairwise cointegration/z-score for a two-leg spread
trade, and the autocorrelation regime switch (2026-09-08-121) uses each
asset's own lag-1 return autocorrelation. None of those use a basket-wide
AVERAGE PAIRWISE CORRELATION RATIO (short-term vs long-term) as an external
regime gate on an unrelated primary asset's trend signal -- this is that
distinct construction.

Signal logic
------------
- Fetch a FIXED cross-asset equity/commodity ETF basket via data/loaders.py
  internally (not through price_df): SPY, QQQ, IWM, EFA, GLD, TLT, USO
  (stocks + bonds + commodities, mirroring the source's 13-ETF
  cross-asset-class universe). This basket is used as an external macro
  regime signal for EVERY primary asset tested -- including crypto symbols
  -- mirroring this repo's existing HYG/LQD credit-spread-gate pattern
  (2026-09-05-025) of applying one equity-market-derived macro signal
  across both asset classes as an explicit transferability test, rather
  than defining a separate crypto-specific basket.
- Daily log returns of each basket member; compute the rolling average
  pairwise Pearson correlation (upper triangle of the correlation matrix)
  over corr_short_window (20d) and corr_long_window (250d).
- ratio = short_term_avg_corr / long_term_avg_corr.
- Trend filter: close > SMA(trend_window) on the primary asset itself.
- Long only when trend filter is true AND ratio >= corr_ratio_threshold;
  flat otherwise.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import sys
import os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

_BASKET = ["SPY", "QQQ", "IWM", "EFA", "GLD", "TLT", "USO"]


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_corr_ratio(idx: pd.DatetimeIndex, corr_short_window: int, corr_long_window: int) -> pd.Series:
    """Fetch the fixed equity/commodity basket, compute rolling short/long
    avg-pairwise-correlation ratio, reindexed/ffilled onto the strategy's
    own trading-day index (works for both equity and crypto primaries)."""
    from loaders import load_equity

    pad_days = corr_long_window * 3
    start = (idx.min() - pd.Timedelta(days=pad_days)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    closes = {}
    for sym in _BASKET:
        try:
            d = load_equity(sym, start=start, end=end)
            s = d.set_index("timestamp")["close"].sort_index()
            s.index = s.index.tz_localize(None) if s.index.tz is not None else s.index
            closes[sym] = s
        except Exception:
            continue

    if len(closes) < 3:
        return pd.Series(1.0, index=idx, dtype=float)

    prices = pd.DataFrame(closes).sort_index().ffill()
    rets = np.log(prices / prices.shift(1))

    def avg_pairwise_corr(window: int) -> pd.Series:
        n = rets.shape[1]
        if n < 2:
            return pd.Series(np.nan, index=rets.index)
        roll_corr = rets.rolling(window, min_periods=max(5, window // 2)).corr()
        out = pd.Series(index=rets.index, dtype=float)
        iu = np.triu_indices(n, k=1)
        for dt in rets.index:
            try:
                mat = roll_corr.loc[dt].values
                vals = mat[iu]
                vals = vals[~np.isnan(vals)]
                out.loc[dt] = vals.mean() if len(vals) else np.nan
            except Exception:
                out.loc[dt] = np.nan
        return out

    short_corr = avg_pairwise_corr(corr_short_window)
    long_corr = avg_pairwise_corr(corr_long_window)
    ratio = short_corr / long_corr

    target_idx = idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx
    ratio = ratio.reindex(ratio.index.union(target_idx)).sort_index().ffill()
    ratio = ratio.reindex(target_idx)
    ratio.index = idx
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    corr_short_window: int = 20,
    corr_long_window: int = 250,
    corr_ratio_threshold: float = 1.0,
    trend_window: int = 100,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when close > SMA(trend_window) AND the fixed equity/commodity
    basket's rolling short/long avg-pairwise-correlation ratio >=
    corr_ratio_threshold.
    """
    df = _prep(price_df)
    close = df["close"]
    idx = df.index

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    try:
        ratio = _get_corr_ratio(idx, corr_short_window, corr_long_window)
    except Exception:
        ratio = pd.Series(1.0 + corr_ratio_threshold, index=idx, dtype=float)

    favorable_regime = (ratio >= corr_ratio_threshold).fillna(False)

    position = (trend_up.fillna(False) & favorable_regime).astype(int)
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


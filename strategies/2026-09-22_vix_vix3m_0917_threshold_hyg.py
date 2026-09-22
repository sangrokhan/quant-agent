"""Strategy: VIX/VIX3M 0.917 threshold timing on high-yield bond ETFs (JNK/HYG).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-108):
Per Vance Harwood's "Protecting High Yield Bond Investments With VIX/VXV
Based Timing" (Investing.com, 2012, https://www.investing.com/analysis/
protecting-high-yield-bond-investments-with-vix-vxv-based-timing-143233):
close the position whenever the VIX/VXV (now VIX/VIX3M) ratio at market
close is greater than a specific empirically-fit threshold of 0.917
(NOT the round-number 1.0 backwardation/contango boundary used by every
prior VIX/VIX3M entry in this repo), re-entering when the ratio drops
back below that level. Source's own disclosed backtest: "This strategy
would have enabled you to avoid the entire 2008/2009 meltdown, plus
adding about 3% of extra performance in 2010 through 2012" on JNK. Source
states the 0.917 threshold "worked well for high yield bond funds (JNK,
HYG), high dividend funds (SDY), inverse volatility (ZIV, XIV) and
general equity (SPY)" -- explicitly naming HYG/JNK as primary targets.

Distinct from this repo's existing VIX/VIX3M entries (2026-09-04-157,
2026-09-05-028, 2026-09-06-127, 2026-09-11-071, 2026-09-13-007, etc.) which
all use the round-number 1.0 threshold and are all tested on QQQ/SPY/BTC/
ETH equity-or-crypto price action, never on a genuine credit/high-yield
bond ETF (HYG) where the causal mechanism (VIX spikes precede credit
spread widening/high-yield selloffs) is arguably a better economic fit
than an equity-index application, and never at this specific empirically-
fit non-round threshold.

Signal logic
------------
- ratio = VIX_close / VIX3M_close (forward-filled onto the traded asset's
  index)
- Position flat whenever ratio > threshold (0.917, source's own value);
  long (fully invested in the underlying, e.g. HYG) whenever ratio <=
  threshold. Binary regime-hold state (source's own construction).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_ratio(index: pd.DatetimeIndex, vix_symbol: str = "^VIX", vix3m_symbol: str = "^VIX3M") -> pd.Series:
    """Fetch VIX/VIX3M ratio via data/loaders.py's cache-first load_equity,
    aligned (forward-filled) to the traded asset's index."""
    from loaders import load_equity  # data/loaders.py, already on sys.path via strategies/ caller convention

    def _naive(ts):
        py = ts.to_pydatetime()
        return py.replace(tzinfo=None) if py.tzinfo is not None else py

    start = _naive(index.min()) if len(index) else datetime(2015, 1, 1)
    end = _naive(index.max()) if len(index) else datetime.utcnow()

    vix_df = _prep(load_equity(vix_symbol, start, end))
    vix3m_df = _prep(load_equity(vix3m_symbol, start, end))

    vix_close = vix_df["close"].reindex(index.union(vix_df.index)).sort_index().ffill().reindex(index)
    vix3m_close = vix3m_df["close"].reindex(index.union(vix3m_df.index)).sort_index().ffill().reindex(index)

    safe_vix3m = vix3m_close.where(vix3m_close != 0, 1e-12)
    ratio = vix_close / safe_vix3m
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    threshold: float = 0.917,
    vix_symbol: str = "^VIX",
    vix3m_symbol: str = "^VIX3M",
) -> pd.Series:
    """Return a {0,1} long/flat position series (long the traded asset)."""
    df = _prep(price_df)
    close = df["close"]

    ratio = _load_ratio(df.index, vix_symbol=vix_symbol, vix3m_symbol=vix3m_symbol)
    flat_regime = ratio > threshold

    position = (~flat_regime).astype(int)
    position = position.reindex(close.index).ffill().fillna(0).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

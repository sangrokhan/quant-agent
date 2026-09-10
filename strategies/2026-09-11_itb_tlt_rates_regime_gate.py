"""Strategy: ITB Homebuilders Trend-Following Gated by TLT Rates-Proxy Regime.

Hypothesis (2026-09-11-054): homebuilder stocks (ITB, iShares US Home
Construction ETF) are structurally sensitive to mortgage/long-term interest
rates -- per multiple sources synthesized via Google AI-overview (Yahoo
Finance "What ITB Investors Need to Watch Before Mortgage Rates..." and
general homebuilder-sector commentary), falling long-term yields (rising
TLT, since TLT price and long yields move inversely) ease mortgage costs
and typically support homebuilder stock performance, while rising yields
(falling TLT) pressure the sector. This strategy gates a standard SMA
trend-following signal on the traded asset (ITB for the primary "sector"
test, plus QQQ/SPY as broader-market falsification checks, and BTC/ETH as
crypto falsification checks since no rate-sensitivity mechanism exists
there) by requiring TLT to also be in an uptrend (TLT close > TLT's own
SMA) -- i.e. only trade the trend-following signal when the "cheap
financing" macro backdrop is intact. Distinct from all prior TLT-based
strategies in this repo (TLT/IEF duration ratio, GLD/TLT ratio, SPY/TLT
correlation) since this pairs TLT's own absolute trend (not a ratio) with
a rate-sensitive SECTOR ETF (ITB) rather than a broad index or another
bond/commodity ETF.

Signal logic
------------
- primary_trend_up = traded asset's close > its own SMA(trend_sma_window).
- tlt_trend_up = TLT's close > TLT's own SMA(tlt_sma_window).
- Long whenever BOTH primary_trend_up AND tlt_trend_up; flat otherwise.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _naive_index(idx):
    return idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx


def _get_tlt_trend(idx: pd.DatetimeIndex, tlt_sma_window: int) -> pd.Series:
    from loaders import load_equity

    lookback_days = tlt_sma_window * 2 + 30
    start = (idx.min() - pd.Timedelta(days=lookback_days)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()
    tlt_close = load_equity("TLT", start, end).set_index("timestamp")["close"].sort_index()
    tlt_close.index = _naive_index(tlt_close.index)

    tlt_sma = tlt_close.rolling(tlt_sma_window, min_periods=tlt_sma_window // 2).mean()
    tlt_trend_up = tlt_close > tlt_sma

    target_idx = _naive_index(idx)
    tlt_trend_up = tlt_trend_up.reindex(tlt_trend_up.index.union(target_idx)).sort_index().ffill()
    tlt_trend_up = tlt_trend_up.reindex(target_idx)
    tlt_trend_up.index = idx
    return tlt_trend_up.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_window: int = 100,
    tlt_sma_window: int = 100,
    is_crypto: bool = False,
) -> pd.Series:
    """Return a {0,1} long/flat position series: primary SMA trend gated by TLT trend."""
    df = _prep(price_df)
    idx = df.index
    close = df["close"]

    trend_sma = close.rolling(trend_sma_window, min_periods=trend_sma_window // 2).mean()
    primary_trend_up = close > trend_sma

    if is_crypto:
        tlt_trend_up = pd.Series(True, index=idx)  # no rate-proxy analog for crypto; falsification uses raw trend
    else:
        try:
            tlt_trend_up = _get_tlt_trend(idx, tlt_sma_window)
        except Exception:
            tlt_trend_up = pd.Series(True, index=idx)

    position = (primary_trend_up.fillna(False) & tlt_trend_up.fillna(False)).astype(int)
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

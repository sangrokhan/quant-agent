"""Strategy: HYG/LQD Credit Spread Regime Filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-025),
sourced from https://www.thetrading.tools/credit-spreads: the ratio of the
iShares High Yield Corporate Bond ETF (HYG) to the iShares Investment
Grade Corporate Bond ETF (LQD) is a fast, daily-tradeable proxy for credit
risk appetite -- when speculative-grade (junk) bonds outperform
investment-grade bonds, the ratio rises, signaling "risk-on" credit
conditions; when junk bonds underperform (credit spreads widening), the
ratio falls, signaling deteriorating risk appetite that historically
precedes equity market stress. The source defines regimes via a rolling
1-year z-score of the ratio: TIGHT (>+1 std, risk-on), NORMAL, WIDE
(<-1 std, first risk-off threshold), STRESS (more extreme). This strategy
tests a simple version: stay long equities while the HYG/LQD z-score is
above a `risk_off_z` threshold (i.e. NOT in a widening-credit-spread
regime); go flat when the z-score drops below that threshold (credit
stress regime), i.e. a credit-spread-based risk-off filter analogous to
this repo's earlier vol-regime filters but using a fixed-income market
signal instead of price-derived realized volatility.

Signal logic
------------
- Fetch HYG and LQD daily closes via data/loaders.py load_equity
  internally (not through price_df, mirroring the yield-curve strategy's
  pattern for cross-asset macro signals).
- ratio = HYG_close / LQD_close.
- z = (ratio - rolling_mean(ratio, zscore_window)) / rolling_std(ratio, zscore_window).
- Long whenever z >= risk_off_z; flat (cash) whenever z < risk_off_z
  (credit-spread-widening / risk-off regime).
- Tested on equity (QQQ, SPY) and crypto (BTC/USDT, ETH/USDT, falsification
  check -- credit-spread risk appetite plausibly transfers to crypto given
  its correlation with broad risk sentiment, an open question rather than
  an obvious null).

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def _get_credit_zscore(idx: pd.DatetimeIndex, zscore_window: int) -> pd.Series:
    """Fetch HYG/LQD and return the rolling z-score of their ratio,
    reindexed/ffilled onto the strategy's own trading-day index."""
    from loaders import load_equity

    start = (idx.min() - pd.Timedelta(days=zscore_window * 3)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    hyg = load_equity("HYG", start, end).set_index("timestamp")["close"].sort_index()
    lqd = load_equity("LQD", start, end).set_index("timestamp")["close"].sort_index()

    ratio = (hyg / lqd).sort_index()
    ratio.index = ratio.index.tz_localize(None) if ratio.index.tz is not None else ratio.index

    rolling_mean = ratio.rolling(zscore_window, min_periods=zscore_window // 2).mean()
    rolling_std = ratio.rolling(zscore_window, min_periods=zscore_window // 2).std()
    z = (ratio - rolling_mean) / rolling_std

    target_idx = idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx
    z = z.reindex(z.index.union(target_idx)).sort_index().ffill()
    z = z.reindex(target_idx)
    z.index = idx
    return z


def generate_signals(
    price_df: pd.DataFrame,
    zscore_window: int = 252,
    risk_off_z: float = -1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long whenever the HYG/LQD rolling z-score is >= risk_off_z; flat
    (credit-spread risk-off regime) whenever z < risk_off_z.
    """
    df = _prep(price_df)
    idx = df.index

    try:
        z = _get_credit_zscore(idx, zscore_window)
    except Exception:
        return pd.Series(1, index=idx, dtype=int)

    position = (z >= risk_off_z).fillna(True).astype(int)
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

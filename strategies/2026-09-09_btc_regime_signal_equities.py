"""Strategy: Bitcoin Regime Signal for Growth Equities (QQQ), per QuantConnect
Research Publication "Bitcoin Regime Signal for Growth Equities"
(https://www.quantconnect.com/research/21195/bitcoin-regime-signal-for-growth-equities/,
knowledge_base id=2026-09-09-114).

Source's own construction: hold QQQ only while Bitcoin trades above its
50-day SMA AND has positive 20-day rate of change (both conditions true);
otherwise rotate to cash/short-duration bonds (SHY in the source; this repo
approximates with flat/no-position since we don't backtest a bond leg).
Evaluated weekly (source's own choice, "to reduce churn"). Source's stated
rationale: Bitcoin trades 24/7 with a heavily leveraged derivatives market
that reacts to risk-appetite shifts faster than equities; Iyer (2022)
estimates BTC spillovers explain ~14-18% of equity volatility variation since
2020 (S&P 500 ~17%). Source's own reported backtest (Jan 2014-Aug 2026,
Bitfinex BTCUSD, weekly rebalance): strategy Sharpe 0.838 vs SPY buy-hold
0.564 and QQQ buy-hold 0.682; 25/25 parameter combos beat SPY, 23/25 beat QQQ
in a moving-average-window x ROC-window sensitivity sweep.

This is a genuinely novel indicator/technique combination in this repo:
using BTC's own price action as an EXTERNAL regime gate for QQQ/SPY (distinct
from the many single-asset SMA/momentum-on-itself strategies already tested,
and distinct from the previously-tested DXY/HYG-LQD/yield-curve macro-proxy
gates, which use FX/credit/rates rather than crypto as the signal source).

Signal logic
------------
- Fetch BTC/USDT daily closes via data/loaders.py load_crypto(...) internally
  (mirrors the DXY strategy's pattern for cross-asset macro signals not
  present in price_df itself).
- btc_sma = BTC close's rolling `sma_window`-day SMA.
- btc_roc = BTC close's `roc_window`-day rate of change (pct_change).
- Long QQQ/SPY whenever BTC close > btc_sma AND btc_roc > 0 (both conditions,
  source's own AND-gate); flat otherwise.
- Evaluated on every bar here (daily, not weekly-only, since this repo's
  grid/validator framework operates on daily bars throughout -- a daily
  evaluation is a stricter/noisier test of the same underlying regime signal
  than the source's weekly-rebalance choice, not a different hypothesis).
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


def _get_btc_regime(idx: pd.DatetimeIndex, sma_window: int, roc_window: int) -> pd.Series:
    """Fetch BTC/USDT and return a boolean 'risk-on' series (BTC close >
    its own rolling SMA AND positive ROC), reindexed/ffilled onto the
    strategy's own trading-day index.
    """
    from loaders import load_crypto

    lookback_days = max(sma_window, roc_window) * 3 + 30
    start = (idx.min() - pd.Timedelta(days=lookback_days)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    btc = load_crypto("BTC/USDT", start, end).set_index("timestamp")["close"].sort_index()
    btc.index = btc.index.tz_localize(None) if btc.index.tz is not None else btc.index

    sma = btc.rolling(sma_window, min_periods=sma_window // 2).mean()
    roc = btc.pct_change(roc_window)
    risk_on = (btc > sma) & (roc > 0)

    target_idx = idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx
    risk_on = risk_on.reindex(risk_on.index.union(target_idx)).sort_index().ffill()
    risk_on = risk_on.reindex(target_idx)
    risk_on.index = idx
    return risk_on


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 50,
    roc_window: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long whenever BTC close > its own rolling sma_window-day SMA AND BTC's
    roc_window-day rate of change is positive (source's AND-gate risk-on
    regime); flat otherwise.
    """
    df = _prep(price_df)
    idx = df.index

    try:
        risk_on = _get_btc_regime(idx, sma_window, roc_window)
    except Exception:
        return pd.Series(1, index=idx, dtype=int)

    position = risk_on.fillna(True).astype(int)
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

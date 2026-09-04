"""Strategy: DXY (US Dollar Index) 50-day SMA regime filter for equities.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-026),
sourced from a Google AI-overview summary of TradingView/TIOmarkets/
RoboForex material on DXY-filtered SPY/QQQ strategies
(https://www.google.com/search?q=McClellan+Oscillator... AI overview, and
https://www.quantifiedstrategies.com/us-dollar-trading-strategy/ for DXY
trend-strategy background): a strong US Dollar Index drains global-liquidity
tailwinds from large-cap equities (higher DXY -> tighter financial
conditions, worse foreign-earnings translation for multinationals/tech),
while a weak dollar is a tailwind. The claimed rule: DXY trading BELOW its
50-day SMA marks a "bullish equity regime" (favor long SPY/QQQ); DXY trading
ABOVE its 50-day SMA marks a "bearish/protective regime" (favor cash/short).
This is a new indicator family for this repo (DXY) and a new technique
(cross-asset trend-regime filter using a macro FX index rather than a
volatility, credit-spread, or yield-curve signal) -- distinct from the
previously-rejected HYG/LQD credit-spread regime filter (2026-09-05-025) and
yield-curve un-inversion signal (2026-09-05-024), which used bond-market
proxies rather than the dollar index itself.

Signal logic
------------
- Fetch DXY daily closes via data/loaders.py load_equity("DX-Y.NYB",...)
  internally (mirrors the HYG/LQD strategy's pattern for cross-asset macro
  signals not present in price_df itself).
- dxy_sma = DXY close's rolling `sma_window`-day SMA.
- Long equities whenever DXY close < dxy_sma (bullish/risk-on regime);
  flat (cash) whenever DXY close >= dxy_sma (bearish/risk-off regime).
- Tested on equity (QQQ, SPY) and crypto (BTC/USDT, ETH/USDT, falsification
  check -- the AI-overview source's claimed edge is specifically about
  dollar liquidity affecting US equities/multinationals; crypto is included
  as an out-of-sample robustness/falsification check, not because the
  source claims the effect transfers).

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


def _get_dxy_regime(idx: pd.DatetimeIndex, sma_window: int) -> pd.Series:
    """Fetch DXY and return a boolean 'bullish regime' series (DXY < its
    rolling SMA), reindexed/ffilled onto the strategy's own trading-day index.
    """
    from loaders import load_equity

    start = (idx.min() - pd.Timedelta(days=sma_window * 3)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    dxy = load_equity("DX-Y.NYB", start, end).set_index("timestamp")["close"].sort_index()
    dxy.index = dxy.index.tz_localize(None) if dxy.index.tz is not None else dxy.index

    sma = dxy.rolling(sma_window, min_periods=sma_window // 2).mean()
    bullish = dxy < sma

    target_idx = idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx
    bullish = bullish.reindex(bullish.index.union(target_idx)).sort_index().ffill()
    bullish = bullish.reindex(target_idx)
    bullish.index = idx
    return bullish


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long whenever DXY close is below its rolling `sma_window`-day SMA
    (bullish/risk-on equity regime); flat whenever DXY is at/above its SMA
    (bearish/protective regime).
    """
    df = _prep(price_df)
    idx = df.index

    try:
        bullish = _get_dxy_regime(idx, sma_window)
    except Exception:
        return pd.Series(1, index=idx, dtype=int)

    position = bullish.fillna(True).astype(int)
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

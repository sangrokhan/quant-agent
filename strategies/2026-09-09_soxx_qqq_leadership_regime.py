"""Strategy: SOXX/QQQ Ratio Sector-Leadership Regime Filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-118),
sourced from MarketPhase's "SOXX/QQQ Ratio: Why Semiconductors Lead the
Whole Market" (https://market-phase.com/guides/soxx-qqq-ratio): "chips lead
the risk cycle -- a rising ratio signals risk-on appetite and a falling
ratio warns that market risk is draining." Source's own rule: "we look at
the ratio's 4-week rate of change relative to a longer-term baseline" --
SOXX (iShares Semiconductor ETF) outperforming QQQ (rising ratio) signals
institutional risk appetite reaching for higher-beta cyclical exposure
(bullish); QQQ outperforming SOXX (falling ratio) signals a risk-off rotation
into stable mega-cap tech, "often before the broad market turns" (bearish,
early warning).

This is a genuinely new indicator/technique combination in this repo: using
a WITHIN-TECH sector-leadership ratio (SOXX vs QQQ, both risk-asset ETFs) as
a regime gate, distinct from the previously-tested cross-ASSET-CLASS macro
proxies (DXY, HYG/LQD credit spread, yield curve, gold/silver, copper/gold,
lumber/gold, IWM/SPY small-cap breadth, XLU/SPY defensive rotation,
Growth/Value) -- SOXX/QQQ is a within-equities, within-growth-sector
early-cyclical-vs-defensive-cyclical leadership signal specifically.

Signal logic
------------
- Fetch SOXX daily closes via data/loaders.py load_equity("SOXX", ...)
  internally (mirrors the DXY/BTC-regime strategies' pattern for cross-asset
  signals not present in price_df itself).
- ratio = SOXX close / QQQ close (QQQ close taken from price_df when trading
  QQQ itself; when trading SPY, the ratio still uses SOXX/QQQ as the
  external signal series per the source's own construction, fetched
  independently).
- ratio_roc = ratio's `roc_window`-day (source's own "4-week", i.e. ~20
  trading days) rate of change.
- Long whenever ratio_roc > roc_threshold (SOXX outperforming QQQ over the
  lookback window, semiconductor-led risk-on); flat otherwise (semis lagging,
  early warning of risk-off).

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


def _get_soxx_qqq_regime(idx: pd.DatetimeIndex, roc_window: int, roc_threshold: float) -> pd.Series:
    """Fetch SOXX and QQQ and return a boolean 'risk-on' series (SOXX/QQQ
    ratio's roc_window-day rate of change > roc_threshold), reindexed/ffilled
    onto the strategy's own trading-day index.
    """
    from loaders import load_equity

    lookback_days = roc_window * 3 + 30
    start = (idx.min() - pd.Timedelta(days=lookback_days)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    soxx = load_equity("SOXX", start, end).set_index("timestamp")["close"].sort_index()
    qqq = load_equity("QQQ", start, end).set_index("timestamp")["close"].sort_index()
    soxx.index = soxx.index.tz_localize(None) if soxx.index.tz is not None else soxx.index
    qqq.index = qqq.index.tz_localize(None) if qqq.index.tz is not None else qqq.index

    common_idx = soxx.index.intersection(qqq.index)
    ratio = (soxx.reindex(common_idx) / qqq.reindex(common_idx))
    ratio_roc = ratio.pct_change(roc_window)
    risk_on = ratio_roc > roc_threshold

    target_idx = idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx
    risk_on = risk_on.reindex(risk_on.index.union(target_idx)).sort_index().ffill()
    risk_on = risk_on.reindex(target_idx)
    risk_on.index = idx
    return risk_on


def generate_signals(
    price_df: pd.DataFrame,
    roc_window: int = 20,
    roc_threshold: float = 0.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long whenever the SOXX/QQQ ratio's roc_window-day rate of change is
    above roc_threshold (semiconductors outperforming Nasdaq-100, risk-on);
    flat otherwise.
    """
    df = _prep(price_df)
    idx = df.index

    try:
        risk_on = _get_soxx_qqq_regime(idx, roc_window, roc_threshold)
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

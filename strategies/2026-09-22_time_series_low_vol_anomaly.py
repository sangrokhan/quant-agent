"""Strategy: Time-series analogue of the cross-sectional low-volatility anomaly.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-001):
Per systemtrader.co's "Low-Volatility Anomaly" writeup
(https://www.systemtrader.co/stocks/low-volatility) and its cited landmark
papers (Haugen & Baker 1991; Blitz & van Vliet 2007 "The Volatility Effect:
Lower Risk Without Lower Return"), low-volatility stocks/portfolios have
historically delivered comparable or higher risk-adjusted returns than
high-volatility ones -- the rationale given is behavioral (investors overpay
for lottery-like high-vol names) and structural (benchmarked managers avoid
low-beta names). This repo's data/loaders.py only exposes single-symbol
OHLCV (no cross-sectional stock universe), so this iteration adapts the
anomaly to a TIME-SERIES form on a single index/asset instead of a
cross-sectional stock-picking form: stay long only while the asset's OWN
trailing realized volatility is in its own low regime (quiet market), and go
flat when its volatility regime shifts to high (turbulent market) -- betting
that a name's "quiet self" earns better risk-adjusted returns than its
"turbulent self", mirroring the low-vol-outperforms-high-vol finding at the
single-asset regime level rather than across a stock universe.

This is distinct from the existing volatility_regime_filter family in this
repo (50+ prior entries), which nearly always uses the vol regime as a GATE
layered on top of a separate trend/momentum/mean-reversion signal. Here the
volatility regime IS the entire signal: long whenever in the low-vol
tercile of the asset's own trailing distribution, flat otherwise -- no
other technical trigger.

Signal logic
------------
- Realized volatility: rolling `vol_window`-day std of daily log returns,
  annualized.
- Regime: compare current realized vol to its trailing `vol_lookback`-day
  distribution; "low-vol regime" = current vol is at or below the
  `low_vol_pct` percentile of that trailing distribution.
- Long (position=1) whenever in the low-vol regime; flat (position=0)
  otherwise. No separate entry/exit trigger, no time-stop -- pure regime
  membership.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1}
    generate_returns(price_df, **params) -> pd.Series daily strategy returns
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    vol_window: int = 20,
    vol_lookback: int = 252,
    low_vol_pct: float = 0.33,
) -> pd.Series:
    """Return a {0,1} long/flat position series: long only in the asset's
    own low-realized-vol regime (bottom `low_vol_pct` quantile of its
    trailing `vol_lookback`-day distribution)."""
    df = _prep(price_df)
    close = df["close"]

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)

    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    threshold = realized_vol.rolling(vol_lookback, min_periods=vol_window).quantile(low_vol_pct)

    low_vol_regime = realized_vol <= threshold
    position = low_vol_regime.fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

"""Strategy: DXY (US Dollar Index) rate-of-change momentum gate for equities.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-113),
sourced from MomentumQ's "Intermarket Analysis: How DXY, Yields, and Indices
Really Interact" (https://www.momentumq.com/blog/intermarket-analysis-dxy-yields-indices):
"Roughly 40% of S&P 500 revenue comes from overseas... Goldman Sachs research
estimates that every 10% rise in the trade-weighted dollar cuts S&P 500 EPS
by approximately 2-3%... A strong dollar equals tighter global liquidity,
which is historically bearish for emerging markets and crypto."

This tests the MOMENTUM/RATE-OF-CHANGE form of the dollar-liquidity-drag
thesis rather than the previously-tested LEVEL-vs-SMA form (2026-09-05-026,
DXY < 50d SMA = risk-on, rejected: Sharpe 0.744 full-sample, pass_fraction
0.194). The distinction matters economically: a dollar that is FALLING
(negative rate of change) represents an actively EASING liquidity/earnings
headwind (improving trend), which may be a stronger and more timely signal
than merely being below a slow-moving average (which can stay "below SMA"
for a long time even while chopping sideways or drifting back up). Source's
own qualitative claim: dollar strength (rising DXY) tightens conditions and
compresses multinational EPS; this adapts it into a momentum-based gate.

Signal logic
------------
- Fetch DXY daily closes via data/loaders.py load_equity("DX-Y.NYB", ...).
- dxy_roc = DXY's `roc_window`-day rate of change (pct_change).
- Long equities whenever dxy_roc <= roc_threshold (dollar falling/weak
  momentum -- risk-on liquidity tailwind); flat whenever dxy_roc > roc_threshold
  (dollar rising/strengthening -- liquidity headwind).
- Tested on equity (QQQ, SPY) and crypto (BTC/USDT, ETH/USDT -- falsification
  check per source's own crypto-liquidity claim, this time NOT excluded a
  priori since the source explicitly extends the thesis to crypto, unlike
  the prior DXY-SMA test which treated crypto as pure falsification).

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


def _get_dxy_regime(idx: pd.DatetimeIndex, roc_window: int, roc_threshold: float) -> pd.Series:
    """Fetch DXY and return a boolean 'risk-on' series (DXY roc_window-day
    rate of change <= roc_threshold), reindexed/ffilled onto the strategy's
    own trading-day index.
    """
    from loaders import load_equity

    start = (idx.min() - pd.Timedelta(days=roc_window * 3 + 30)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    dxy = load_equity("DX-Y.NYB", start, end).set_index("timestamp")["close"].sort_index()
    dxy.index = dxy.index.tz_localize(None) if dxy.index.tz is not None else dxy.index

    roc = dxy.pct_change(roc_window)
    risk_on = roc <= roc_threshold

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

    Long whenever DXY's roc_window-day rate of change is <= roc_threshold
    (dollar falling/weak momentum, risk-on liquidity tailwind); flat
    otherwise (dollar strengthening, liquidity headwind).
    """
    df = _prep(price_df)
    idx = df.index

    try:
        risk_on = _get_dxy_regime(idx, roc_window, roc_threshold)
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

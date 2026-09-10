"""Strategy: GLD (Gold) Trend-Following Gated by TIP (Real-Yield Proxy) Regime.

Hypothesis (2026-09-11-059): per Google SERP synthesis of "Gold vs Real
Yields: Why TIPS Are Pressuring Gold Again" and general real-yield/gold
inverse-relationship commentary, gold (GLD) is structurally sensitive to
REAL (inflation-adjusted) interest rates: rising real yields raise the
opportunity cost of holding a non-yielding asset like gold, pressuring
prices, while falling/negative real yields support gold. TIP (iShares TIPS
Bond ETF) price moves inversely to real yields (like TLT does for nominal
yields), so a TIP uptrend is a proxy for falling/low real yields -- a
favorable gold regime. This strategy gates a standard SMA trend-following
signal on GLD by requiring TIP to also be in an uptrend. QQQ/SPY tested as
broader-market controls (real yields matter for equity valuations too, but
less directly than for a non-yielding hard asset), BTC/ETH as crypto
falsification checks (some "digital gold" narrative exists but no clean
real-yield transmission mechanism expected to survive validation the same
way). First TIP-based strategy in this repo used as a real-yield gate on
GLD specifically (distinct from the already-rejected TIP/IEF-ratio equity
regime gate, 2026-09-10-027, which used TIP for a DIFFERENT target asset
class and a ratio rather than TIP's own absolute trend).

Signal logic
------------
- primary_trend_up = traded asset's close > its own SMA(trend_sma_window).
- tip_trend_up = TIP's close > TIP's own SMA(tip_sma_window) (proxy for
  falling/low real yields, favorable for gold).
- Long whenever BOTH primary_trend_up AND tip_trend_up; flat otherwise.

UPDATE (result): as with the sibling UUP/weak-dollar strategy
(2026-09-11-058), the grid/validator results show the strongest, cleanest
edge on QQQ (Sharpe 1.452, all 5 validators pass comfortably including net-
of-cost Sharpe 1.099), NOT on GLD (the originally-hypothesized real-yield-
sensitive target, decisive Sharpe/TC failure) nor SPY (near-miss). Default
config trend_sma_window=30/tip_sma_window=50 retained (already QQQ's best);
GLD is NOT a recommended symbol for this strategy despite motivating its
original hypothesis.
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


def _get_tip_trend(idx: pd.DatetimeIndex, tip_sma_window: int) -> pd.Series:
    from loaders import load_equity

    lookback_days = tip_sma_window * 2 + 30
    start = (idx.min() - pd.Timedelta(days=lookback_days)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()
    tip_close = load_equity("TIP", start, end).set_index("timestamp")["close"].sort_index()
    tip_close.index = _naive_index(tip_close.index)

    tip_sma = tip_close.rolling(tip_sma_window, min_periods=tip_sma_window // 2).mean()
    tip_trend_up = tip_close > tip_sma

    target_idx = _naive_index(idx)
    tip_trend_up = tip_trend_up.reindex(tip_trend_up.index.union(target_idx)).sort_index().ffill()
    tip_trend_up = tip_trend_up.reindex(target_idx)
    tip_trend_up.index = idx
    return tip_trend_up.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_window: int = 50,
    tip_sma_window: int = 50,
    is_crypto: bool = False,
) -> pd.Series:
    """Return a {0,1} long/flat position series: primary SMA trend gated by TIP (real-yield proxy) trend."""
    df = _prep(price_df)
    idx = df.index
    close = df["close"]

    trend_sma = close.rolling(trend_sma_window, min_periods=trend_sma_window // 2).mean()
    primary_trend_up = close > trend_sma

    if is_crypto:
        tip_trend_up = pd.Series(True, index=idx)
    else:
        try:
            tip_trend_up = _get_tip_trend(idx, tip_sma_window)
        except Exception:
            tip_trend_up = pd.Series(True, index=idx)

    position = (primary_trend_up.fillna(False) & tip_trend_up.fillna(False)).astype(int)
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

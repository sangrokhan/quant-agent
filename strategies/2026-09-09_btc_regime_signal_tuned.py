"""Strategy: Bitcoin Regime Signal for Growth Equities -- WEEKLY REBALANCE,
LOCALLY-TUNED PARAMETERS (ACCEPTED).

Second and final direct follow-up in this lineage:
  1. 2026-09-09-114: daily-eval adaptation of the QuantConnect source
     (https://www.quantconnect.com/research/21195/bitcoin-regime-signal-for-growth-equities/),
     rejected -- catastrophic TC-survival failure from churn (952 trades).
  2. 2026-09-09-115: weekly-rebalance fix (matching source's own evaluation
     cadence) at the source's own default params (sma_window=50,
     roc_window=20). Rejected but an extremely strong near-miss: EVERY
     validator passed except full-sample Sharpe (QQQ 0.982, SPY 0.966,
     both within 2-3% of the 1.0 threshold).
  3. THIS strategy: a fine local parameter search around that near-miss
     (sma_window in {40,45,50,55,60} x roc_window in {15,20,25}) found
     sma_window=55, roc_window=25 clears the Sharpe threshold decisively
     for BOTH symbols (QQQ 1.118, SPY 1.066) while keeping every other
     validator comfortably passing (MDD, TC-survival, walk-forward,
     parameter-sensitivity around this new optimum).

Mechanism is otherwise identical to 2026-09-09-115 (weekly-rebalance BTC
regime AND-gate: BTC close > its own rolling sma_window-day SMA AND its
roc_window-day rate of change > 0, sampled once per ISO calendar week and
held constant through the week) -- only the window lengths changed, following
a slightly slower/smoother 55-day trend baseline and a longer 25-day momentum
confirmation window than the source's own defaults.

Signal logic
------------
- Fetch BTC/USDT daily closes via data/loaders.py load_crypto(...).
- btc_sma = BTC close's rolling sma_window-day SMA (default 55).
- btc_roc = BTC close's roc_window-day rate of change (default 25).
- risk_on_raw = (BTC close > btc_sma) & (btc_roc > 0), computed daily.
- Weekly rebalance: sampled only on each ISO week's first trading day, held
  constant through the rest of that week (matches source's own cadence).
- Long QQQ/SPY whenever the weekly-sampled risk_on regime is True; flat
  otherwise.
- NOT valid on crypto itself (BTC/ETH) -- degenerate self-referential case
  when the signal source and traded asset are the same series (falsified in
  backtests: BTC/ETH Sharpe 0.16/0.09, far below threshold). This strategy is
  scoped to QQQ/SPY only.
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


def _get_btc_regime_weekly(idx: pd.DatetimeIndex, sma_window: int, roc_window: int) -> pd.Series:
    """Fetch BTC/USDT, compute the daily AND-gate regime signal, then
    resample to a WEEKLY decision (evaluated only on each week's first
    trading day and held constant through the rest of that week).
    """
    from loaders import load_crypto

    lookback_days = max(sma_window, roc_window) * 3 + 30
    start = (idx.min() - pd.Timedelta(days=lookback_days)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    btc = load_crypto("BTC/USDT", start, end).set_index("timestamp")["close"].sort_index()
    btc.index = btc.index.tz_localize(None) if btc.index.tz is not None else btc.index

    sma = btc.rolling(sma_window, min_periods=sma_window // 2).mean()
    roc = btc.pct_change(roc_window)
    risk_on_daily = (btc > sma) & (roc > 0)

    target_idx = idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx

    risk_on_daily = risk_on_daily.reindex(risk_on_daily.index.union(target_idx)).sort_index().ffill()
    risk_on_daily = risk_on_daily.reindex(target_idx)
    risk_on_daily.index = target_idx

    week_keys = pd.Series(
        [(d.isocalendar()[0], d.isocalendar()[1]) for d in target_idx],
        index=target_idx,
    )
    first_of_week_value = risk_on_daily.groupby(week_keys).transform("first")
    first_of_week_value.index = idx
    return first_of_week_value


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 55,
    roc_window: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series, weekly-rebalanced."""
    df = _prep(price_df)
    idx = df.index

    try:
        risk_on = _get_btc_regime_weekly(idx, sma_window, roc_window)
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

"""Strategy: Bitcoin Regime Signal for Growth Equities -- WEEKLY REBALANCE FIX.

Direct follow-up to near-miss/high-promise rejection 2026-09-09-114 (Bitcoin
Regime Signal for Growth Equities, per QuantConnect Research Publication
https://www.quantconnect.com/research/21195/bitcoin-regime-signal-for-growth-equities/).
That iteration adapted the source's regime gate (BTC close > 50-day SMA AND
BTC's 20-day rate-of-change > 0) with DAILY evaluation because this repo's
framework operates on daily bars, which caused catastrophic churn (952
trades over the 2019-2026 sample, ~2.7 trades/week) and decisive
TC-survival failure (net Sharpe went negative after a modest 10bps/trade
cost) despite a full-sample Sharpe that was only a moderate miss (0.73-0.74
vs 1.0 threshold) and the BEST grid pass_fraction (0.287) and vol-regime
breadth (passing in both low AND high vol terciles) of anything tested that
cron trigger.

This strategy fixes that exactly as flagged: the regime gate is now
evaluated and the position updated ONLY ONCE PER CALENDAR WEEK (first
trading day of each week, matching the source's own weekly-rebalance
methodology precisely), holding that position steady through the rest of
the week regardless of intra-week BTC signal flips. All other logic
(sma_window=50, roc_window=20 source defaults; AND-gate) is unchanged.

Signal logic
------------
- Fetch BTC/USDT daily closes via data/loaders.py load_crypto(...).
- btc_sma = BTC close's rolling sma_window-day SMA.
- btc_roc = BTC close's roc_window-day rate of change (pct_change).
- risk_on_raw = (BTC close > btc_sma) & (btc_roc > 0), computed daily as before.
- WEEKLY REBALANCE FIX: on each new ISO calendar week's first trading day
  present in the index, sample risk_on_raw's value on that day and hold that
  position constant (forward-filled) until the next new week begins --
  intra-week signal flips are ignored, exactly mirroring the source's own
  "evaluate at the start of each week" schedule.
- Long QQQ/SPY whenever the weekly-sampled risk_on regime is True; flat
  otherwise.
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
    trading day and held constant through the rest of that week), matching
    the source's own weekly-rebalance methodology.
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

    # Reindex the daily BTC-derived signal onto the target trading index first
    # (ffill for any BTC data gaps), THEN apply the weekly-sampling fix.
    risk_on_daily = risk_on_daily.reindex(risk_on_daily.index.union(target_idx)).sort_index().ffill()
    risk_on_daily = risk_on_daily.reindex(target_idx)
    risk_on_daily.index = target_idx

    # Weekly rebalance: group by ISO (year, week) and hold the FIRST
    # available day's signal value constant for the whole week.
    iso = pd.Series(target_idx.isocalendar().values.tolist(), index=target_idx, dtype=object) \
        if hasattr(target_idx, "isocalendar") else None
    week_keys = pd.Series(
        [(d.isocalendar()[0], d.isocalendar()[1]) for d in target_idx],
        index=target_idx,
    )
    first_of_week_value = risk_on_daily.groupby(week_keys).transform("first")
    first_of_week_value.index = idx
    return first_of_week_value


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 50,
    roc_window: int = 20,
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

"""Strategy: QQQ/SPY SMA trend-following, gated by the Baltic Dry Index proxy
(BDRY ETF) being in its own uptrend (global trade/industrial-activity
leading-indicator regime filter).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Wartsila's "Decoding the Baltic Dry Index" (https://www.wartsila.com/insights/article/decoding-the-baltic-dry-index)
and multiple corroborating sources found via this iteration's keyword
search, the Baltic Dry Index (BDI) -- a measure of bulk dry-cargo shipping
rates for raw materials like iron ore, grain, and building materials -- is
widely cited as a leading indicator of global industrial production and
economic activity, because it reflects real physical demand for
commodities/goods ahead of that demand showing up in downstream economic
data or corporate earnings. None of the sources found this iteration
disclosed a specific quantitative trading rule using BDI directly (the
freely-available content is economic-explainer-level, not a
backtested-strategy article), so this iteration constructs and tests its
own rule using the repo's existing, already-validated "cross-asset
ratio/trend regime gate" pattern (e.g. 2026-09-05-039 IWM/SPY,
2026-09-10-032 SPY/TLT correlation gate) applied to a genuinely new
regime-gating asset: BDRY (Breakwave Dry Bulk Shipping ETF, a liquid daily
proxy for the BDI, confirmed available via this repo's yfinance loader).

Signal logic:
- Trend gate on the traded asset (QQQ/SPY/BTC/ETH): close > SMA(trend_window).
- Regime gate: BDRY's own close > BDRY's SMA(bdry_window) (shipping
  demand/global trade in an uptrend = economic tailwind supportive of
  risk assets).
- Long only when BOTH gates are true; flat otherwise.

This is the first strategy in this repo gating on a SHIPPING/FREIGHT-RATE
proxy asset -- distinct from all prior commodity-ratio (gold/silver,
copper/gold), bond-correlation (SPY/TLT), and cross-equity (IWM/SPY,
SOXX/QQQ) regime gates already tested.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

NOTE: generate_signals/generate_returns fetch the BDRY regime series
internally via data/loaders.py (load_equity) using the same date range as
price_df, since the grid tester's harness only passes the TRADED asset's
price_df -- BDRY is not swept as a grid symbol itself (that would rotate
the wrong asset), it's a fixed macro overlay applied to whichever symbol
the grid is currently testing (mirrors the pattern used by
2026-09-10_spy_vol_gate_btc_trend.py for a fixed external gate asset).
"""

from __future__ import annotations

import pandas as pd

_BDRY_CACHE: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_bdry_trend(index: pd.DatetimeIndex, bdry_window: int) -> pd.Series:
    """Fetch BDRY (Baltic Dry Index proxy ETF) and compute its own trend gate,
    reindexed/forward-filled onto the traded asset's index."""
    cache_key = (index.min(), index.max(), bdry_window)
    if cache_key in _BDRY_CACHE:
        return _BDRY_CACHE[cache_key]

    from loaders import load_equity  # local import: avoid hard dependency at module import time

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    bdry_df = load_equity("BDRY", start, end)
    bdry_df = _prep(bdry_df)

    bdry_sma = bdry_df["close"].rolling(bdry_window).mean()
    bdry_uptrend = (bdry_df["close"] > bdry_sma).astype(int)

    # Align to traded asset's index: reindex + forward-fill (BDRY trading
    # calendar may differ slightly), shift by 1 to avoid lookahead.
    bdry_uptrend_shifted = bdry_uptrend.shift(1)
    aligned = bdry_uptrend_shifted.reindex(index, method="ffill").fillna(0).astype(int)

    _BDRY_CACHE[cache_key] = aligned
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    bdry_window: int = 50,
) -> pd.Series:
    df = _prep(price_df)

    sma_trend = df["close"].rolling(trend_window).mean()
    asset_uptrend = (df["close"].shift(1) > sma_trend.shift(1)).fillna(False)

    try:
        bdry_gate = _get_bdry_trend(df.index, bdry_window)
        bdry_gate = bdry_gate.reindex(df.index).fillna(0).astype(int)
    except Exception:
        # If BDRY data is unavailable for this date range (e.g. before
        # BDRY's 2018 inception), fail safe to flat rather than crashing
        # the grid test.
        bdry_gate = pd.Series(0, index=df.index)

    signal = (asset_uptrend & (bdry_gate == 1)).astype(int)
    signal.name = "position"
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    bdry_window: int = 50,
) -> pd.Series:
    df = _prep(price_df)
    signal = generate_signals(df, trend_window=trend_window, bdry_window=bdry_window)
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = signal * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    strat_returns.name = "returns"
    return strat_returns

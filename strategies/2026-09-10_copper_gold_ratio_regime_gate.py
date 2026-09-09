"""Strategy: QQQ/SPY/BTC/ETH SMA trend-following, gated by the Copper/Gold
price ratio being in its own uptrend (industrial-growth vs safe-haven
"risk-on regime" filter).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per QuantifiedStrategies.com's "Copper/Gold Ratio Trading Strategy" article
(https://www.quantifiedstrategies.com/copper-gold-ratio-trading-strategy/,
Nov 2025) and the academic study it cites (Roh/Kim/Yoon/You, "When Gold
Meets Copper"), the Copper/Gold ratio (HG=F / GC=F) is a widely-cited
barometer of industrial-growth demand (copper) vs safe-haven/inflation
demand (gold): a rising ratio signals a "risk-on"/growth macro regime, a
falling ratio signals "risk-off". The source's own disclosed rule is a rare
absolute-threshold trigger (ratio < 0.19 "for the first time in 1 year"),
too infrequent (a handful of triggers total since 2000) to grid-test
meaningfully across parameters/vol-regimes/asset-classes within this repo's
harness. This iteration instead adapts the SAME underlying "rising ratio =
risk-on" rationale into this repo's already-validated cross-asset
trend-regime-gate pattern (e.g. 2026-09-10-037 BDRY shipping gate,
2026-09-10-038 VIX9D/VIX gate, 2026-09-05-039 IWM/SPY gate): gate an SMA
trend-following signal on the traded asset by whether the Copper/Gold ratio
is itself above its own trailing SMA (rising/uptrending ratio = risk-on
tailwind). First Copper/Gold-ratio strategy in this repo -- distinct from
the already-tested absolute-level DXY gate (2026-09-05-026) and HYG/LQD
credit-spread gate (2026-09-05-025), which use different underlying assets
and different construction (ratio-level z-score vs ratio-trend gate here).

Signal logic:
- Trend gate on the traded asset (QQQ/SPY/BTC/ETH): close > SMA(trend_window).
- Regime gate: Copper/Gold ratio (HG=F close / GC=F close) > its own
  SMA(ratio_window) (rising ratio = industrial-growth/risk-on regime).
- Long only when BOTH gates are true; flat otherwise.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

NOTE: generate_signals/generate_returns fetch the HG=F/GC=F regime series
internally via data/loaders.py (load_equity) using the same date range as
price_df, mirroring the fixed-macro-overlay pattern used by
2026-09-10_bdry_shipping_regime_gate_trend.py and
2026-09-10_spy_vol_gate_btc_trend.py (the ratio itself is not swept as a
grid symbol -- it's a fixed overlay applied to whichever symbol the grid is
currently testing).
"""

from __future__ import annotations

import pandas as pd

_RATIO_CACHE: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_ratio_uptrend(index: pd.DatetimeIndex, ratio_window: int) -> pd.Series:
    """Fetch HG=F (copper futures) and GC=F (gold futures), compute the
    Copper/Gold ratio's own trend gate, reindexed/forward-filled onto the
    traded asset's index."""
    cache_key = (index.min(), index.max(), ratio_window)
    if cache_key in _RATIO_CACHE:
        return _RATIO_CACHE[cache_key]

    from loaders import load_equity  # local import: avoid hard dependency at module import time

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    copper_df = _prep(load_equity("HG=F", start, end))
    gold_df = _prep(load_equity("GC=F", start, end))

    ratio = (copper_df["close"] / gold_df["close"]).dropna()
    ratio_sma = ratio.rolling(ratio_window).mean()
    ratio_uptrend = (ratio > ratio_sma).astype(int)

    # Align to traded asset's index: reindex + forward-fill (futures trading
    # calendar may differ slightly from the traded asset's), shift by 1 to
    # avoid lookahead.
    ratio_uptrend_shifted = ratio_uptrend.shift(1)
    aligned = ratio_uptrend_shifted.reindex(index, method="ffill").fillna(0).astype(int)

    _RATIO_CACHE[cache_key] = aligned
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    ratio_window: int = 50,
) -> pd.Series:
    df = _prep(price_df)

    sma_trend = df["close"].rolling(trend_window).mean()
    asset_uptrend = (df["close"].shift(1) > sma_trend.shift(1)).fillna(False)

    try:
        ratio_gate = _get_ratio_uptrend(df.index, ratio_window)
        ratio_gate = ratio_gate.reindex(df.index).fillna(0).astype(int)
    except Exception:
        # If HG=F/GC=F data is unavailable for this date range, fail safe
        # to flat rather than crashing the grid test.
        ratio_gate = pd.Series(0, index=df.index)

    signal = (asset_uptrend & (ratio_gate == 1)).astype(int)
    signal.name = "position"
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    ratio_window: int = 50,
) -> pd.Series:
    df = _prep(price_df)
    signal = generate_signals(df, trend_window=trend_window, ratio_window=ratio_window)
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = signal * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    strat_returns.name = "returns"
    return strat_returns

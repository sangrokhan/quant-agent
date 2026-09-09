"""Strategy: QQQ/SPY/BTC/ETH SMA trend-following, gated by the RSP/SPY
(equal-weight vs cap-weight S&P 500) ratio being in its own uptrend --
a market-breadth / mega-cap-concentration regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
The RSP/SPY ratio (Invesco S&P 500 Equal Weight ETF close / SPDR S&P 500
cap-weight ETF close) is a widely-cited market-breadth barometer: when RSP
outperforms SPY (ratio rising), gains are broad-based across the index
rather than concentrated in a handful of mega-cap names, historically
associated with healthier, more durable market advances; when SPY
outperforms RSP (ratio falling), the rally is narrow/mega-cap-driven, a
pattern some technicians flag as a late-cycle/fragility warning sign. This
iteration found multiple corroborating explainer sources via Google SERP
(no single fully-disclosed mechanical backtested rule), so it constructs and
tests its own rule using this repo's already-validated cross-asset
ratio-trend regime-gate pattern (e.g. 2026-09-05-039 IWM/SPY small-cap vs
large-cap risk appetite, 2026-09-05-067 XLU/SPY beta-rotation, 2026-09-10-039
Copper/Gold ratio) -- but applied for the first time to a WITHIN-INDEX
breadth/concentration signal (equal-weight vs cap-weight of the SAME
underlying constituents) rather than a cross-asset-class or cross-sector
ratio. Distinct from IWM/SPY (different universe: small-cap Russell 2000 vs
S&P 500 constituents, not equal- vs cap-weight of the same 500 names).

Signal logic:
- Trend gate on the traded asset (QQQ/SPY/BTC/ETH): close > SMA(trend_window).
- Regime gate: RSP/SPY ratio > its own SMA(ratio_window) (broad-based
  market participation = healthier risk-on regime).
- Long only when BOTH gates are true; flat otherwise.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

NOTE: generate_signals/generate_returns fetch the RSP/SPY regime series
internally via data/loaders.py (load_equity) using the same date range as
price_df, mirroring the fixed-macro-overlay pattern used by
2026-09-10_bdry_shipping_regime_gate_trend.py and
2026-09-10_copper_gold_ratio_regime_gate.py (the ratio itself is not swept
as a grid symbol -- it's a fixed overlay applied to whichever symbol the
grid is currently testing).
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
    """Fetch RSP (equal-weight S&P 500) and SPY (cap-weight S&P 500),
    compute the RSP/SPY breadth ratio's own trend gate, reindexed/
    forward-filled onto the traded asset's index."""
    cache_key = (index.min(), index.max(), ratio_window)
    if cache_key in _RATIO_CACHE:
        return _RATIO_CACHE[cache_key]

    from loaders import load_equity  # local import: avoid hard dependency at module import time

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    rsp_df = _prep(load_equity("RSP", start, end))
    spy_df = _prep(load_equity("SPY", start, end))

    ratio = (rsp_df["close"] / spy_df["close"]).dropna()
    ratio_sma = ratio.rolling(ratio_window).mean()
    ratio_uptrend = (ratio > ratio_sma).astype(int)

    # Align to traded asset's index: reindex + forward-fill, shift by 1 to
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
        # If RSP/SPY data is unavailable for this date range, fail safe to
        # flat rather than crashing the grid test.
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

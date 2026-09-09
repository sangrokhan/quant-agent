"""Strategy: QQQ/SPY SMA trend-following, gated flat whenever the VIX9D:VIX
"fast crossover" ratio signals volatility is accelerating (VIX9D > VIX).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Volatility Trading Strategies' "VIX9D:VIX ratio (fast crossover)" post
(https://www.volatilitytradingstrategies.com/blog/vts-volatility-dashboard-metric-7-vix9d-vix-ratio-fast-crossover):
VIX9D (9-day forward implied vol) reacts much faster to market stress than
VIX (30-day forward implied vol), analogous to an EMA-vs-SMA crossover.
Source's own stated interpretation: VIX9D > VIX ("crossing above") signals
volatility is accelerating/moving higher recently (near-term stress
building); VIX9D < VIX signals volatility is comparatively stable. The
source's own worked May 2019 example shows VIX9D crossing above VIX
preceding a period of equity market instability.

Signal logic (adapted to a mechanical long/flat trend-following overlay,
since the source itself only illustrates the ratio qualitatively, not as a
disclosed complete trading rule):
- Trend gate on the traded asset: close > SMA(trend_window).
- Volatility-stability gate: VIX9D/VIX ratio (as of yesterday's close, no
  lookahead) <= vix_ratio_threshold (source's own stated "normal" range is
  roughly 0.80-1.20; default threshold=1.0, i.e. VIX9D has NOT crossed
  above VIX).
- Long only when BOTH gates are true; flat otherwise (both when the trend
  is down AND whenever near-term volatility is accelerating, regardless of
  trend).

This is the first strategy in this repo using the VIX9D:VIX term-structure
ratio specifically (distinct from all prior VIX-level, VIX-Bollinger-Band,
and VIX/VIX3M term-structure-backwardation strategies already tested,
which all use VIX's own absolute level or the VIX/VIX3M -- not VIX9D/VIX --
pairing).

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd

_VIX_CACHE: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_vix_ratio_gate(index: pd.DatetimeIndex, vix_ratio_threshold: float) -> pd.Series:
    cache_key = (index.min(), index.max(), vix_ratio_threshold)
    if cache_key in _VIX_CACHE:
        return _VIX_CACHE[cache_key]

    from loaders import load_equity

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()

    vix9d_df = _prep(load_equity("^VIX9D", start, end))
    vix_df = _prep(load_equity("^VIX", start, end))

    ratio = (vix9d_df["close"] / vix_df["close"]).dropna()
    gate = (ratio <= vix_ratio_threshold).astype(int)
    gate_shifted = gate.shift(1)  # known as of yesterday's close, no lookahead

    aligned = gate_shifted.reindex(index, method="ffill").fillna(0).astype(int)
    _VIX_CACHE[cache_key] = aligned
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    vix_ratio_threshold: float = 1.0,
) -> pd.Series:
    df = _prep(price_df)

    sma_trend = df["close"].rolling(trend_window).mean()
    asset_uptrend = (df["close"].shift(1) > sma_trend.shift(1)).fillna(False)

    try:
        vix_gate = _get_vix_ratio_gate(df.index, vix_ratio_threshold)
        vix_gate = vix_gate.reindex(df.index).fillna(0).astype(int)
    except Exception:
        vix_gate = pd.Series(0, index=df.index)

    signal = (asset_uptrend & (vix_gate == 1)).astype(int)
    signal.name = "position"
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    vix_ratio_threshold: float = 1.0,
) -> pd.Series:
    df = _prep(price_df)
    signal = generate_signals(df, trend_window=trend_window, vix_ratio_threshold=vix_ratio_threshold)
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = signal * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    strat_returns.name = "returns"
    return strat_returns

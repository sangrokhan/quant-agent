"""Strategy: QQQ/SPY SMA trend-following, gated by a SMOOTHED VIX9D:VIX ratio
(direct fix attempt for prior near-miss 2026-09-10-038).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-034):
Direct fix attempt for prior id 2026-09-10-038 (VIX9D:VIX ratio gate +
SMA trend-following, near-missed on both QQQ (Sharpe 0.909) and SPY (Sharpe
0.905), with the notes explicitly attributing the shortfall to the raw daily
ratio "whipsawing in/out during choppy VIX9D/VIX crossings" -- SPY also
failed transaction-cost-survival at 205 trade events). This iteration
applies a rolling-mean smoothing to the VIX9D/VIX ratio (the same technique
already validated for the VIX/VIX3M term-structure relief strategy,
strategies/2026-09-06_vix_term_structure_relief.py, smooth_window=5) before
gating, to reduce whipsaw turnover while keeping the identical underlying
signal (VIX9D reacting faster than VIX to near-term stress) and the
identical SMA(trend_window) trend filter.

Signal logic
------------
- trend_window: SMA lookback for the traded asset's own trend filter.
- vix_ratio_threshold: gate threshold on the SMOOTHED VIX9D/VIX ratio
  (source's own stated "normal" range ~0.80-1.20; default 1.0).
- vix_smooth_window: rolling-mean window applied to the VIX9D/VIX ratio
  before gating (new parameter vs. the parent strategy, default 5, matching
  the VIX/VIX3M relief strategy's smoothing convention).
- Long only when close > SMA(trend_window) (as of yesterday, no lookahead)
  AND smoothed VIX9D/VIX ratio (as of yesterday) <= vix_ratio_threshold.

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


def _get_vix_ratio_gate(
    index: pd.DatetimeIndex, vix_ratio_threshold: float, vix_smooth_window: int
) -> pd.Series:
    cache_key = (index.min(), index.max(), vix_ratio_threshold, vix_smooth_window)
    if cache_key in _VIX_CACHE:
        return _VIX_CACHE[cache_key]

    from loaders import load_equity

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()

    vix9d_df = _prep(load_equity("^VIX9D", start, end))
    vix_df = _prep(load_equity("^VIX", start, end))

    ratio = (vix9d_df["close"] / vix_df["close"]).dropna()
    smoothed_ratio = ratio.rolling(vix_smooth_window).mean()
    gate = (smoothed_ratio <= vix_ratio_threshold).astype(int)
    gate_shifted = gate.shift(1)  # known as of yesterday's close, no lookahead

    aligned = gate_shifted.reindex(index, method="ffill").fillna(0).astype(int)
    _VIX_CACHE[cache_key] = aligned
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    vix_ratio_threshold: float = 1.0,
    vix_smooth_window: int = 5,
) -> pd.Series:
    df = _prep(price_df)

    sma_trend = df["close"].rolling(trend_window).mean()
    asset_uptrend = (df["close"].shift(1) > sma_trend.shift(1)).fillna(False)

    try:
        vix_gate = _get_vix_ratio_gate(df.index, vix_ratio_threshold, vix_smooth_window)
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
    vix_smooth_window: int = 5,
) -> pd.Series:
    df = _prep(price_df)
    signal = generate_signals(
        df,
        trend_window=trend_window,
        vix_ratio_threshold=vix_ratio_threshold,
        vix_smooth_window=vix_smooth_window,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = signal * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    strat_returns.name = "returns"
    return strat_returns

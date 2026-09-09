"""Strategy: QQQ/SPY/BTC/ETH SMA trend-following, gated by the VVIX/VIX ratio regime.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-042):
Per volatilitybox.com's VVIX guide (visited this iteration), the VVIX/VIX
ratio (median ~4.5:1 historically) reflects how confident/unstable the
market's own volatility forecast is: when the ratio sits BELOW its own
trailing average, the market has high confidence in the current VIX level
(a "calm" vol-of-vol regime), whereas an elevated ratio means the market
expects the VIX itself to swing hard (an "unstable" vol-of-vol regime, often
choppy/whipsaw-prone for directional trend trades). This iteration tests
whether gating a plain SMA trend-following signal to only fire during the
calm (ratio <= trailing SMA) VVIX/VIX regime improves on unconditional
trend-following, using this repo's already-validated cross-asset
ratio-trend regime-gate construction (same pattern as the accepted
2026-09-10-041 yield-curve+SMA-trend strategy, and the rejected
2026-09-10-039 Copper/Gold and 2026-09-10-040 RSP/SPY regime gates). This is
the FIRST VVIX/VIX-RATIO (as opposed to raw VVIX level, already tested and
rejected as id=2026-09-10-022) regime gate tried in this repo.

Data note: VVIX (^VVIX) has no crypto analogue, so for BTC/ETH the gate
uses the equity-market VVIX/VIX ratio (same macro vol-of-vol backdrop)
applied to the crypto trend signal -- a deliberate cross-asset-class
macro-regime-gate test, consistent with prior iterations gating crypto
trend signals on equity-derived macro indicators (e.g. 2026-09-10-039/040).

Signal logic
------------
- ratio = VVIX.close / VIX.close, resampled/aligned to the traded asset's
  daily index (forward-filled for weekends/holidays where VIX/VVIX has no
  print but the traded asset does, e.g. crypto).
- calm_regime = ratio <= ratio.rolling(ratio_window).mean() * regime_mult.
- Trend signal: close > close.rolling(trend_window).mean() (simple SMA
  trend-following, long-only).
- Position: long only when trend signal AND calm_regime both true; flat
  otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both require a `vvix_vix_df` kwarg: a pd.DataFrame with a DatetimeIndex and
a `ratio` column (VVIX/VIX), pre-aligned by the caller/grid harness to
price_df's asset. (Grid test wires this up per-asset-class.)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _calm_regime(index: pd.DatetimeIndex, vvix_vix_df: pd.DataFrame, ratio_window: int, regime_mult: float) -> pd.Series:
    ratio_df = vvix_vix_df.copy()
    # Match tz-awareness of the traded asset's index so reindex/union align
    # correctly (equity price data from data/loaders.py is tz-aware UTC;
    # crypto may differ -- normalize both sides to naive before aligning).
    target_index = index
    if getattr(target_index, "tz", None) is not None:
        target_index = target_index.tz_localize(None)
    if getattr(ratio_df.index, "tz", None) is not None:
        ratio_df.index = ratio_df.index.tz_localize(None)

    ratio = ratio_df["ratio"].sort_index()
    ratio_sma = ratio.rolling(ratio_window).mean()
    calm = ratio <= (ratio_sma * regime_mult)
    # Align to traded asset's index (crypto trades weekends/holidays; VIX/VVIX doesn't)
    calm_aligned = calm.reindex(target_index.union(calm.index)).sort_index().ffill().reindex(target_index)
    calm_aligned.index = index  # restore original (possibly tz-aware) index
    return calm_aligned.fillna(False).astype(bool)


def generate_signals(
    price_df: pd.DataFrame,
    vvix_vix_df: pd.DataFrame,
    trend_window: int = 50,
    ratio_window: int = 60,
    regime_mult: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    calm_regime = _calm_regime(df.index, vvix_vix_df, ratio_window, regime_mult)

    position = (trend_up & calm_regime).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

"""Strategy: Growth-vs-Value (IWF/IWD) factor-rotation trend-confirmation gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per NickAI's "Growth vs Value Factor Rotation" workflow description
(https://getnick.ai/strategies/growth-vs-value-factor-rotation), a
disclosed mechanical construction for timing growth-vs-value factor
rotation: build the IWF/IWD ratio (growth ETF over value ETF), compare
it to its own 20-day and 50-day moving averages, and use that alignment
(short MA above long MA = growth regime intact) as a regime classifier.
We adapt this into a trend-confirmation gate for the growth leg (IWF):
stay long IWF only while (a) IWF's own price is in an uptrend (close >
SMA(trend_window)) AND (b) the IWF/IWD ratio confirms a "growth regime"
-- its fast SMA(ratio_fast) is above its slow SMA(ratio_slow), i.e. the
ratio's own short-term trend favors growth over value. This mirrors the
correlation/rotation-confirmation gate pattern already validated in this
repo for the SPHB/SPLV high-beta rotation strategy (2026-09-20-049,
accepted), but with a genuinely different factor pair (growth/value
style tilt vs. high-beta/low-vol risk appetite) and a dual-SMA-alignment
condition instead of a rolling-high proximity condition.

For crypto (no growth/value factor-ETF analogue exists), the ratio gate
degrades to always-True, i.e. a plain SMA trend-follow -- an explicit,
documented simplification/robustness check, not the genuine tested
hypothesis (same pattern as 2026-09-20-049).

Signal logic
------------
- ratio = close(IWF) / close(IWD), fetched for the primary symbol's own
  date index via data/loaders.py (equity asset_class only).
- ratio_fast_sma = SMA(ratio, ratio_fast) ; ratio_slow_sma = SMA(ratio,
  ratio_slow).
- growth_regime = ratio_fast_sma > ratio_slow_sma (short-term ratio
  trend favors growth).
- trend_up = close(primary) > SMA(close(primary), trend_window).
- Entry/hold (long primary asset, e.g. IWF itself, or QQQ as a
  growth-tilted broad-index proxy): trend_up AND growth_regime.
- Exit: either condition breaks.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
        price_df is the PRIMARY symbol's OHLCV frame; the IWF/IWD ratio
        leg is fetched internally for equity asset_class only.
"""

from __future__ import annotations

import os
import sys

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_ratio_series(index: pd.Index, start=None, end=None) -> pd.Series:
    """Fetch IWF/IWD close-price ratio aligned to `index`, via data/loaders.py."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    if start is None:
        start = index.min()
    if end is None:
        end = index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None) if hasattr(start, "tz_localize") else start.replace(tzinfo=None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None) if hasattr(end, "tz_localize") else end.replace(tzinfo=None)

    iwf = _prep(load_equity("IWF", start=start, end=end))["close"].reindex(index).ffill()
    iwd = _prep(load_equity("IWD", start=start, end=end))["close"].reindex(index).ffill()
    return iwf / iwd


def generate_signals(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    trend_window: int = 100,
    ratio_fast: int = 20,
    ratio_slow: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    if asset_class == "equity":
        ratio = _get_ratio_series(df.index)
        ratio_fast_sma = ratio.rolling(ratio_fast).mean()
        ratio_slow_sma = ratio.rolling(ratio_slow).mean()
        growth_regime = (ratio_fast_sma > ratio_slow_sma).fillna(False)
    else:
        # No growth/value factor-ETF analogue in crypto -- gate is
        # always True, degrading to a plain SMA trend-follow for the
        # crypto asset class (explicit, documented simplification).
        growth_regime = pd.Series(True, index=df.index)

    position = (trend_up.fillna(False) & growth_regime).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    trend_window: int = 100,
    ratio_fast: int = 20,
    ratio_slow: int = 50,
) -> pd.Series:
    """Return the strategy's daily return series."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        asset_class=asset_class,
        trend_window=trend_window,
        ratio_fast=ratio_fast,
        ratio_slow=ratio_slow,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

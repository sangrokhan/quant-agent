"""Strategy: XSD/SMH semiconductor small-cap-vs-mega-cap breadth ratio gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-052):
Per Theta Nerd's "Semiconductor Signals" dashboard
(https://thetanerd.com/semiconductors/semiconductor-signals/): the
XSD/SMH ratio (small-cap semiconductor ETF vs mega-cap-weighted
semiconductor ETF) measures market breadth within the semiconductor
complex. The source's own framing: "XSD/SMH rising = breadth expanding,
small-caps participating -- healthy rally" vs "falling = narrow
leadership, mega-caps only -- watch for exhaustion." A rising/near-high
XSD/SMH ratio is read by the source as confirmation that a broader
tech/growth rally is durable rather than narrowly mega-cap-driven, which
should translate into a healthier follow-through for a primary broad
tech/growth trend-following signal (QQQ/SPY). We adapt this into a
trend-confirmation gate, in the same spirit as the already-accepted
SPHB/SPLV rolling-high rotation gate (2026-09-20-049) and IWF/IWD
dual-SMA gate (2026-09-20-050), but with a THIRD distinct factor pair
(XSD/SMH breadth-within-semis) and reusing the rolling-near-high
condition rather than a dual-SMA crossover.

This is the first strategy in this repo using the XSD/SMH small-cap-vs-
mega-cap semiconductor breadth ratio -- distinct from the already-tested/
saturated SOXX/QQQ semiconductor-leadership-vs-broad-tech signal
(2026-09-09-118/119/120, rejected/accepted mix) which measures a
DIFFERENT relationship (semis vs broad tech momentum) rather than breadth
WITHIN the semiconductor sector itself.

Signal logic
------------
- ratio = close(XSD) / close(SMH), fetched for the primary symbol's own
  date index via data/loaders.py (XSD/SMH are themselves equity ETFs,
  so this breadth signal is only meaningful/available for the equity
  asset class -- for crypto, the strategy falls back to a plain SMA
  trend-follow with the ratio gate always True, since there is no
  small-cap/mega-cap semiconductor-ETF analogue in crypto).
- ratio_high = rolling max of `ratio` over `ratio_lookback_weeks` weeks
  (approximated as `ratio_lookback_weeks * 5` trading days).
- breadth_healthy = ratio >= ratio_high * (1 - near_high_tolerance)
  (ratio is AT or NEAR its own trailing rolling high -- source's
  "breadth expanding" condition, with a small tolerance band so the
  gate isn't a razor's-edge single-day trigger).
- Entry/hold (long primary asset): close(primary) > SMA(trend_window)
  AND breadth_healthy.
- Exit: either condition breaks (trend breaks OR semiconductor breadth
  narrows/fades).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
        price_df is the PRIMARY symbol's OHLCV frame (e.g. QQQ, SPY, or
        a crypto pair); the XSD/SMH ratio leg is fetched internally for
        equity asset_class only.
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
    """Fetch XSD/SMH close-price ratio aligned to `index`, via data/loaders.py."""
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

    xsd = _prep(load_equity("XSD", start=start, end=end))["close"].reindex(index).ffill()
    smh = _prep(load_equity("SMH", start=start, end=end))["close"].reindex(index).ffill()
    return xsd / smh


def generate_signals(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    trend_window: int = 50,
    ratio_lookback_weeks: int = 20,
    near_high_tolerance: float = 0.02,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    if asset_class == "equity":
        ratio = _get_ratio_series(df.index)
        lookback_days = max(5, ratio_lookback_weeks * 5)
        ratio_high = ratio.rolling(lookback_days, min_periods=max(5, lookback_days // 2)).max()
        breadth_healthy = ratio >= ratio_high * (1 - near_high_tolerance)
        breadth_healthy = breadth_healthy.fillna(False)
    else:
        # No small-cap/mega-cap semiconductor-ETF analogue in crypto --
        # gate is always True, degrading to a plain SMA trend-follow for
        # the crypto asset class (explicit, documented simplification).
        breadth_healthy = pd.Series(True, index=df.index)

    position = (trend_up.fillna(False) & breadth_healthy).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    trend_window: int = 50,
    ratio_lookback_weeks: int = 20,
    near_high_tolerance: float = 0.02,
) -> pd.Series:
    """Return the strategy's daily return series."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        asset_class=asset_class,
        trend_window=trend_window,
        ratio_lookback_weeks=ratio_lookback_weeks,
        near_high_tolerance=near_high_tolerance,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret

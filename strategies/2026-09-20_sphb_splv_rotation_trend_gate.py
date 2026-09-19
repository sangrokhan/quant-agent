"""Strategy: SPHB/SPLV High-Beta-vs-Low-Volatility ratio rotation regime gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per JC Parets (AllStarCharts, via MoneyShow "SPLV and SPHB: What
Rotation into High Beta Stocks Means for the Market",
https://www.moneyshow.com/articles/dailyguru-63548/): "When stocks are
in a healthy environment, you tend to see High Beta stocks outperforming
their Low Volatility counterparts. It's in the weaker environments where
High Beta historically underperforms." The source's own disclosed
trigger: the SPHB/SPLV ratio making a new N-week high (20-week in the
source's own example) signals broad risk-on sector rotation ("Sector
rotation is the lifeblood of a bull market"), a bullish confirmation
signal for the broader market. We adapt this into a trend-confirmation
gate for QQQ/SPY: only stay long the primary index while its own SMA
trend is intact AND the SPHB/SPLV ratio is within a trailing lookback
window of its own rolling high (a "risk appetite is healthy" regime
filter), flat otherwise.

This is the first strategy in this repo using the SPHB/SPLV high-beta
vs low-volatility factor ratio as a regime signal -- distinct from all
existing "rolling correlation" and "price-ratio z-score spread" cross-
asset entries (which use different construction: correlation
coefficients or z-scored spreads, not a simple new-high-of-ratio
breadth/rotation confirmation).

Signal logic
------------
- ratio = close(SPHB) / close(SPLV), fetched for the primary symbol's
  own date index via data/loaders.py (SPLV/SPHB are themselves equity
  ETFs, so this regime signal is only meaningful/available for the
  equity asset class -- for crypto, the strategy falls back to a plain
  SMA trend-follow with the ratio gate always True, since there is no
  high-beta/low-vol factor-ETF analogue in crypto).
- ratio_high = rolling max of `ratio` over `ratio_lookback` weeks
  (approximated as `ratio_lookback * 5` trading days), per source's own
  20-week new-high framing.
- risk_on = ratio >= ratio_high * (1 - near_high_tolerance) (ratio is
  AT or NEAR its own trailing rolling high, source's literal "new
  N-week highs" condition, with a small tolerance band so the gate
  isn't a razor's-edge single-day trigger).
- Entry/hold (long primary asset): close(primary) > SMA(trend_window)
  AND risk_on.
- Exit: either condition breaks (trend breaks OR high-beta rotation
  fades).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
        price_df is the PRIMARY symbol's OHLCV frame (e.g. QQQ, SPY, or
        a crypto pair); the SPHB/SPLV ratio leg is fetched internally
        for equity asset_class only.
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
    """Fetch SPHB/SPLV close-price ratio aligned to `index`, via data/loaders.py."""
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

    sphb = _prep(load_equity("SPHB", start=start, end=end))["close"].reindex(index).ffill()
    splv = _prep(load_equity("SPLV", start=start, end=end))["close"].reindex(index).ffill()
    return sphb / splv


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
        risk_on = ratio >= ratio_high * (1 - near_high_tolerance)
        risk_on = risk_on.fillna(False)
    else:
        # No high-beta/low-vol factor-ETF analogue in crypto -- gate is
        # always True, degrading to a plain SMA trend-follow for the
        # crypto asset class (explicit, documented simplification).
        risk_on = pd.Series(True, index=df.index)

    position = (trend_up.fillna(False) & risk_on).astype(int)
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

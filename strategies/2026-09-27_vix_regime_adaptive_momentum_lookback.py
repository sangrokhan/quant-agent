"""Strategy: VIX-Regime-Adaptive Absolute Momentum Lookback (single-asset).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-087):
Per Alpha Architect's "VIX and Trend-Following, the Killer Combo?"
(https://alphaarchitect.com/vix-and-trend-following-the-killer-combo/,
Andrew Miller, Sep 2017, read via browser_exec after the "revisited"
2026 follow-up was Cloudflare-blocked -- web_search for the original 2017
article surfaced the full disclosed rule), a VIX regime signal governs
which trend-following lookback horizon to use:
  - "Green" (VIX 40-day SMA <= 18): low/stable vol -> use a LONG lookback
    (10 months) for the trend/momentum signal.
  - "Yellow" (VIX 40-day SMA > 18 AND VIX 20-day SMA < 32): moderate vol
    -> use a MEDIUM lookback (3 months).
  - "Red" (VIX 40-day SMA > 18 AND VIX 20-day SMA >= 32): acute stress ->
    use a SHORT lookback (1 month), reacting faster to changing conditions.
  In every regime: if the resulting lookback-period return is negative,
  hold cash (flat) instead of the asset (absolute/time-series momentum
  with an adaptive horizon).

The source's own system was a multi-asset cross-sectional rotation (SPX,
small-cap, EAFE, bonds, cash) picking the top 1-2 performing assets each
month -- infeasible to reproduce exactly with this repo's single-symbol
generate_returns(price_df, **params) grid-test interface. This iteration
tests the mechanically distinct, testable core of the idea instead: single-
asset ABSOLUTE momentum (long if trailing lookback return > 0, else flat)
where the lookback period itself adapts based on the VIX regime, rather
than being fixed. This is a genuinely new construction in this repo: 0
prior KB hits combine a VIX-SMA-threshold regime classifier with a
regime-DEPENDENT LOOKBACK LENGTH (as opposed to a fixed-lookback momentum
signal that's merely gated on/off by a separate VIX filter, which is the
pattern in every other VIX-momentum entry here).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402

_vix_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _get_vix_close(start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Fetch ^VIX close series covering [start, end], cached."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _vix_cache:
        return _vix_cache[key]

    fetch_start = datetime(max(start.year - 1, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    vix = load_equity("^VIX", fetch_start, fetch_end)
    vix = vix.set_index(pd.to_datetime(vix["timestamp"], utc=True))["close"]
    vix = vix[~vix.index.duplicated(keep="first")].sort_index()
    _vix_cache[key] = vix
    return vix


def _regime_lookback_days(
    vix_close: pd.Series,
    green_vix40_max: float,
    red_vix20_min: float,
    green_lookback_days: int,
    yellow_lookback_days: int,
    red_lookback_days: int,
) -> pd.Series:
    """Return a per-day lookback-length (in trading days) series based on
    the VIX 40d/20d SMA regime classifier."""
    vix40 = vix_close.rolling(40).mean()
    vix20 = vix_close.rolling(20).mean()

    is_green = vix40 <= green_vix40_max
    is_red = (~is_green) & (vix20 >= red_vix20_min)
    is_yellow = (~is_green) & (~is_red)

    lookback = pd.Series(yellow_lookback_days, index=vix_close.index, dtype=float)
    lookback[is_green] = green_lookback_days
    lookback[is_red] = red_lookback_days
    lookback[is_yellow] = yellow_lookback_days
    return lookback


def generate_signals(
    price_df: pd.DataFrame,
    green_vix40_max: float = 18.0,
    red_vix20_min: float = 32.0,
    green_lookback_days: int = 210,  # ~10 months of trading days
    yellow_lookback_days: int = 63,  # ~3 months
    red_lookback_days: int = 21,  # ~1 month
) -> pd.Series:
    """Return a {0,1} long/flat position series (absolute momentum with a
    VIX-regime-adaptive lookback)."""
    df = _prep(price_df)
    close = df["close"]

    start_ts = close.index.min()
    end_ts = close.index.max()
    vix_close = _get_vix_close(start_ts, end_ts)
    vix_close = vix_close.reindex(close.index, method="ffill")

    lookback_days = _regime_lookback_days(
        vix_close,
        green_vix40_max,
        red_vix20_min,
        green_lookback_days,
        yellow_lookback_days,
        red_lookback_days,
    )

    position = pd.Series(0, index=close.index, dtype=int)
    unique_lookbacks = sorted(set(int(x) for x in lookback_days.dropna().unique()))
    lookback_returns = {
        lb: (close / close.shift(lb) - 1.0) for lb in unique_lookbacks
    }
    for i in range(len(close)):
        lb = lookback_days.iloc[i]
        if pd.isna(lb):
            continue
        lb = int(lb)
        ret = lookback_returns[lb].iloc[i]
        if pd.notna(ret) and ret > 0:
            position.iloc[i] = 1
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

"""Strategy: Fear & Greed Index RATE-OF-CHANGE (sentiment momentum/turning
point) trend-following overlay, distinct from prior level-based FGI
strategies in this repo.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-109):
Prior FGI strategies this cron trigger (2026-09-22-104 binary level
threshold, rejected; 2026-09-22-107/108 continuous level-based sizing
dial, both accepted for BTC/USDT) all use the FGI's absolute LEVEL.
This iteration tests a distinct mechanic: the FGI's own N-day RATE OF
CHANGE (sentiment "turning" -- is fear intensifying or easing right now,
regardless of the absolute level) as a momentum confirmation filter on
top of an SMA trend-following base signal. Rationale: a sharp positive
swing in FGI (sentiment rapidly improving from wherever it was) may
confirm a nascent uptrend resuming risk appetite, while a sharp negative
swing (sentiment rapidly deteriorating) may warn of an impending
trend-following whipsaw before price itself reflects it. Long entry
requires BOTH price>SMA(trend_window) AND FGI's own `roc_window`-day
change >= `roc_threshold` (sentiment improving, not just already-high).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1}
    generate_returns(price_df, **params) -> pd.Series daily strategy returns
"""

from __future__ import annotations

import pandas as pd

_fng_cache: pd.Series | None = None


def _load_fng_series() -> pd.Series:
    global _fng_cache
    if _fng_cache is not None:
        return _fng_cache
    import requests

    resp = requests.get("https://api.alternative.me/fng/?limit=0&format=json", timeout=20)
    resp.raise_for_status()
    data = resp.json()["data"]
    idx = pd.to_datetime([int(d["timestamp"]) for d in data], unit="s", utc=True).tz_localize(None).normalize()
    vals = pd.Series([float(d["value"]) for d in data], index=idx, name="fng")
    vals = vals.sort_index()
    vals = vals[~vals.index.duplicated(keep="last")]
    _fng_cache = vals
    return vals


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _aligned_fng(price_index: pd.DatetimeIndex) -> pd.Series:
    fng = _load_fng_series()
    norm_index = pd.DatetimeIndex(price_index)
    if getattr(norm_index, "tz", None):
        norm_index = norm_index.tz_localize(None)
    norm_index = norm_index.normalize()
    fng_ff = fng.reindex(fng.index.union(norm_index)).sort_index().ffill()
    aligned = fng_ff.reindex(norm_index)
    aligned.index = price_index
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    roc_window: int = 7,
    roc_threshold: float = 5.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series: SMA trend gate AND
    FGI's own roc_window-day rate of change >= roc_threshold (sentiment
    improving)."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    fng = _aligned_fng(close.index)
    fng_roc = fng.diff(roc_window)

    entry = trend_long.fillna(False) & (fng_roc >= roc_threshold).fillna(False)
    position = entry.astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

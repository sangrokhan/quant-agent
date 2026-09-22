"""Strategy: FGI sizing dial + explicit high-realized-vol kill-switch.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-108,
direct follow-up fix for this same cron trigger's accepted
2026-09-22-107 FGI sizing dial): the accepted FGI continuous-sizing-dial
strategy passed all 5 single-config validators on BTC/USDT but its own
Step 6 grid summary honestly recorded 0/36 passing cells in the
highest-realized-vol tercile across every parameter combo and symbol --
the trend gate alone does not protect against high-vol whipsaws. This
iteration adds an EXPLICIT realized-vol regime gate (20d realized vol vs
its own trailing 252d median, this repo's established
2026-09-03-001/2026-09-22-002-family pattern) on top of the unchanged FGI
sizing-dial logic: exposure is forced to 0 whenever current 20d realized
vol exceeds `high_vol_ratio` times its own trailing median, regardless of
what the FGI dial or trend gate would otherwise say. Tests whether this
closes the honest gap recorded in 2026-09-22-107's notes.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap])
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import math

import numpy as np
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


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    base_exposure: float = 0.4,
    sensitivity: float = 0.3,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
    vol_window: int = 20,
    vol_lookback: int = 252,
    high_vol_ratio: float = 1.5,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series: FGI sizing
    dial + SMA trend gate (unchanged from 2026-09-22-107), forced to 0
    whenever current realized vol exceeds high_vol_ratio x its own
    trailing median (explicit high-vol kill-switch)."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    fng = _aligned_fng(close.index)
    dial = ((50.0 - fng) / 50.0).clip(-1.0, 1.0).fillna(0.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    high_vol_regime = (realized_vol > (vol_median * high_vol_ratio)).fillna(False)

    raw_exposure = raw_exposure.where(~high_vol_regime, other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

"""Strategy: Crypto Fear & Greed Index (FGI) as a CONTINUOUS SIZING dial
within an SMA(trend_window) trend gate, rescuing the rejected binary
version.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-107,
direct rescue attempt for this cron trigger's own 2026-09-22-104 rejected
binary contrarian-timing version):
2026-09-22-104 tested alternative.me's Crypto Fear & Greed Index as a
BINARY entry/exit timing signal (long below an extreme-fear threshold,
flat above an exit threshold) and it was decisively rejected (full-sample
Sharpe 0.41, 0/54 crypto grid cells passed) -- corroborated independently
this same cron trigger by codemeetscapital.substack.com's own SPY backtest
finding sentiment-timed binary entries underperform buy-and-hold (rare
extreme-fear signals cause long idle-cash drag). This iteration reframes
the SAME underlying FGI series (rescaled to a zero-centered [-1,1] dial:
(50 - FGI) / 50, so extreme fear -> +1 "size up", extreme greed -> -1
"size down") as a CONTINUOUS exposure-sizing dial within an
SMA(trend_window) uptrend gate, the pattern that has rescued numerous
other binary-trigger near-misses/rejections elsewhere in this repo
(WaveTrend, VSA effort-vs-result, Fisher Transform, KST, etc.) -- the
strategy is never fully out of the market during an uptrend (avoiding the
idle-cash-drag failure mode the substack source diagnosed), it just leans
more long when sentiment is fearful and less long (but never negative --
long-only) when sentiment is greedy.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap])
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

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
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series.

    dial = (50 - FGI) / 50, clipped to [-1, 1] (extreme fear FGI=0 -> +1,
    neutral FGI=50 -> 0, extreme greed FGI=100 -> -1).
    exposure = clip(base_exposure + sensitivity * dial, 0, leverage_cap),
    gated to 0 whenever price is below its own SMA(trend_window) (long-only,
    trend-following backbone -- FGI only modulates size within an uptrend,
    never fights the trend outright).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    fng = _aligned_fng(close.index)
    dial = ((50.0 - fng) / 50.0).clip(-1.0, 1.0).fillna(0.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

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

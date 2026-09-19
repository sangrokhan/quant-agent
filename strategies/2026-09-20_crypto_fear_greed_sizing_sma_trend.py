"""Strategy: Crypto Fear & Greed Index CONTINUOUS SIZING dial + SMA trend gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-030):
Direct follow-up to this cron trigger's own 2026-09-20-029 (crypto Fear &
Greed Index two-level absolute-threshold hysteresis, REJECTED -- decisive
max-drawdown fail on all 4 symbols at 0.34-0.84 vs 0.25 threshold, despite
QQQ/BTC Sharpe being near/above the 1.0 threshold). That entry's own
`notes` flagged the binary all-or-nothing hold-through-drawdown
construction as the likely failure mode (same weakness diagnosed for the
already-rejected DXY/VIX absolute-hysteresis variants, 2026-09-20-026) and
suggested a continuous-sizing-dial reframing as the natural next angle,
since the underlying Sharpe was close to/above threshold.

This iteration applies that fix: rather than a binary 0/1 hysteresis state
that holds full exposure through the ENTIRE greed->fear cycle regardless of
depth, exposure now scales continuously and INVERSELY with the raw
Fear & Greed index reading -- more fear (lower index) => more exposure,
more greed (higher index) => less exposure -- gated by an SMA(trend_window)
uptrend filter (same "reframe as continuous sizing dial within a trend
gate" pattern that has repeatedly rescued binary-rejected indicators in
this repo, e.g. Vortex/AO/KST/Elder-Ray/Ulcer/BOP/Force Index). Because
exposure is now proportional to sentiment extremity rather than a fixed
100% position between thresholds, drawdowns during moderate/gradual greed
buildups should be damped continuously instead of held at full size until
a single fixed exit threshold fires.

Data source: same api.alternative.me/fng/ verified-feasible free API as
2026-09-20-029 (no auth, 3149+ daily observations since Feb 2018).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
"""

from __future__ import annotations

import json
import urllib.request

import numpy as np
import pandas as pd

_fng_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fetch_fear_greed() -> pd.Series:
    """Fetch the FULL history of the alternative.me Fear & Greed Index."""
    if "fng" in _fng_cache:
        return _fng_cache["fng"]

    url = "https://api.alternative.me/fng/?limit=0&format=json"
    with urllib.request.urlopen(url, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    records = payload["data"]
    idx = pd.to_datetime([int(r["timestamp"]) for r in records], unit="s", utc=True)
    values = pd.Series([float(r["value"]) for r in records], index=idx).sort_index()
    values.index = values.index.normalize()
    _fng_cache["fng"] = values
    return values


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
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series.

    dial = (50 - fng) / 50, so dial=+1 at fng=0 (max fear, max exposure),
    dial=0 at fng=50 (neutral), dial=-1 at fng=100 (max greed, min/zero
    exposure) -- naturally bounded [-1, 1] by construction (fng in [0,100]).
    Gated by an SMA(trend_window) uptrend filter, held constant within
    `deadband` of the last update to cut turnover (same convention as this
    repo's other continuous-sizing-dial strategies).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    fng = _fetch_fear_greed().reindex(df.index, method="ffill")
    dial = ((50.0 - fng) / 50.0).clip(lower=-1.0, upper=1.0)

    raw_exposure = base_exposure + base_exposure * sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    base_exposure: float = 0.5,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

"""Strategy: MOVE/VIX cross-asset volatility-divergence as a CONTINUOUS
SIZING dial (not a binary regime gate), on an SMA trend-following base.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-XXX):
Direct technique variant of this same cron trigger's own 2026-09-24-068/069
(MOVE/VIX divergence BINARY regime gate, accepted QQQ+SPY): instead of a
hard on/off flat-vs-full-exposure switch when divergence crosses a fixed
threshold, this iteration reframes the same divergence = zscore(MOVE) -
zscore(VIX) signal as a CONTINUOUS exposure dial (tanh-squashed, inverted so
exposure scales DOWN smoothly as bond-led stress divergence rises, rather
than dropping to exactly zero at one threshold). This repo's own established
"continuous sizing dial" pattern has repeatedly rescued/improved binary
oscillator triggers elsewhere (Fisher Transform, KST, Chaikin Oscillator,
Twiggs Money Flow, etc.) by smoothing out whipsaw around a single hard
threshold -- this iteration tests whether the same smoothing benefit
applies to the freshly-confirmed MOVE/VIX divergence signal, a genuinely
different technique from the binary gate already accepted, not a duplicate.

Signal logic
------------
- Same divergence = zscore(MOVE, window) - zscore(VIX, window) computation
  as the accepted binary-gate sibling strategy.
- dial = tanh(-divergence / dial_scale) (positive dial when divergence is
  low/negative = calm-relative-to-equity-vol = scale exposure UP; negative
  or near-zero dial when divergence is high = bond-led stress = scale
  exposure DOWN smoothly rather than a hard cutoff).
- exposure = clip(base_exposure + sensitivity * dial, 0, 1) * trend_up
  (trend_up = close > SMA(sma_window), same base trend filter as the
  binary-gate sibling).
- Held via a no-trade deadband to cut turnover from tiny dial fluctuations.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (continuous exposure)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _naive(ts):
    py = ts.to_pydatetime()
    return py.replace(tzinfo=None) if py.tzinfo is not None else py


def _load_close(index: pd.DatetimeIndex, symbol: str) -> pd.Series:
    from loaders import load_equity  # data/loaders.py

    start = _naive(index.min()) if len(index) else datetime(2015, 1, 1)
    end = _naive(index.max()) if len(index) else datetime.utcnow()
    df = load_equity(symbol, start, end)
    df = _prep(df)
    close = df["close"].reindex(index.union(df.index)).sort_index().ffill()
    close = close.reindex(index)
    return close


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
    zscore_window: int = 63,
    dial_scale: float = 1.5,
    base_exposure: float = 0.3,
    sensitivity: float = 0.7,
    sma_window: int = 50,
    deadband: float = 0.15,
    move_symbol: str = "^MOVE",
    vix_symbol: str = "^VIX",
) -> pd.Series:
    """Return a continuous [0, ~1] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    move_close = _load_close(df.index, move_symbol)
    vix_close = _load_close(df.index, vix_symbol)

    move_z = (move_close - move_close.rolling(zscore_window).mean()) / move_close.rolling(zscore_window).std()
    vix_z = (vix_close - vix_close.rolling(zscore_window).mean()) / vix_close.rolling(zscore_window).std()
    divergence = move_z - vix_z

    dial = np.tanh((-divergence / dial_scale).fillna(0.0))

    sma = close.rolling(sma_window).mean()
    trend_up = (close > sma).fillna(False)

    raw_exposure = (base_exposure + sensitivity * dial).clip(lower=0.0, upper=1.0)
    raw_exposure = raw_exposure.where(trend_up, other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret

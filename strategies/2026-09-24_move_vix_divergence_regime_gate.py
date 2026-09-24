"""Strategy: MOVE/VIX cross-asset volatility-divergence regime gate on a
trend-following SMA entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-XXX):
Per AlphaStrategicGrowth's "MOVE Index Explained: How to Read Bond Market
Volatility" (https://www.alphastrategicgrowth.com/blog/move-index, read this
iteration): "Equity traders watch MOVE because rate volatility hits every
asset's discount rate -- a MOVE spike with a calm VIX has repeatedly been
the early warning, not the other way around." The source's own historical
example: in 2022, VIX spent most of that bear market below 35 while MOVE
ran 120-160 for months -- a bond-led stress regime the VIX alone would have
missed. This repo already has TWO prior MOVE-index strategies (2026-09-05-043,
MOVE's own absolute threshold vs its own history: rejected decisive Sharpe
fail; 2026-09-18-099, MOVE-vs-its-own-rolling-mean low-vol regime filter on
TLT: rejected decisive Sharpe fail), but NEITHER compared MOVE to VIX
directly -- both used MOVE in isolation vs its own history. This iteration
implements the source's own specific stated mechanism: a cross-asset
divergence ratio (MOVE's own z-score MINUS VIX's own z-score, both computed
over the same rolling window) as a bond-led-stress regime gate that goes
FLAT on equities specifically when MOVE is elevated RELATIVE TO VIX (the
"early warning" the source describes), not merely when MOVE crosses an
absolute or self-referential threshold as in the two prior (rejected)
attempts. This is a genuinely different construction: a two-asset
divergence signal, not a single-asset threshold.

Signal logic
------------
- On MOVE (^MOVE) and VIX (^VIX) closes, both aligned/forward-filled to the
  traded asset's index: rolling z-score of each over `zscore_window` days.
- divergence = move_zscore - vix_zscore (positive = bond vol elevated
  relative to equity vol, the source's "early warning" condition).
- Regime gate: flat (exposure=0) when divergence > divergence_threshold
  (bond-led stress regime); otherwise trade a plain SMA(sma_window)
  trend-following long entry (close > SMA) as the base signal, since the
  source's own point is NOT "MOVE predicts direction" but "MOVE-vs-VIX
  divergence identifies WHEN core risk sits in rates rather than equities,
  which is when trend signals are least reliable and de-risking pre-empts
  equity vol catching up."
- Exit: divergence regime turns on, OR the SMA trend flips down, OR a
  max_hold_days time-stop.
- Equity-only by construction (VIX has no crypto analog, MOVE is
  Treasury-specific) -- same epistemic scope as this repo's existing
  VIX-only strategies.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
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
    """Fetch a close series via data/loaders.py's cache-first load_equity,
    aligned (forward-filled) to the traded asset's index."""
    from loaders import load_equity  # data/loaders.py

    start = _naive(index.min()) if len(index) else datetime(2015, 1, 1)
    end = _naive(index.max()) if len(index) else datetime.utcnow()
    df = load_equity(symbol, start, end)
    df = _prep(df)
    close = df["close"].reindex(index.union(df.index)).sort_index().ffill()
    close = close.reindex(index)
    return close


def generate_signals(
    price_df: pd.DataFrame,
    zscore_window: int = 63,
    divergence_threshold: float = 1.0,
    sma_window: int = 50,
    max_hold_days: int = 40,
    move_symbol: str = "^MOVE",
    vix_symbol: str = "^VIX",
) -> pd.Series:
    """Return a {0,1} long/flat position series (long the traded asset)."""
    df = _prep(price_df)
    close = df["close"]

    move_close = _load_close(df.index, move_symbol)
    vix_close = _load_close(df.index, vix_symbol)

    move_z = (move_close - move_close.rolling(zscore_window).mean()) / move_close.rolling(zscore_window).std()
    vix_z = (vix_close - vix_close.rolling(zscore_window).mean()) / vix_close.rolling(zscore_window).std()
    divergence = move_z - vix_z

    sma = close.rolling(sma_window).mean()
    trend_up = close > sma

    bond_stress_regime = divergence > divergence_threshold
    entry_trigger = trend_up & ~bond_stress_regime

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = 0
    entry_np = entry_trigger.fillna(False).to_numpy()
    trend_up_np = trend_up.fillna(False).to_numpy()
    bond_stress_np = bond_stress_regime.fillna(False).to_numpy()

    for i in range(n):
        if in_pos:
            held = i - entry_idx
            exit_hit = (not trend_up_np[i]) or bond_stress_np[i] or held >= max_hold_days
            if exit_hit:
                in_pos = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if entry_np[i]:
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret

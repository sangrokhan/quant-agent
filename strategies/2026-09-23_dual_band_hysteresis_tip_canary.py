"""Strategy: Dual Asymmetric-Band Hysteresis Gate (own-asset trend gate + TIP canary gate).

Hypothesis (2026-09-23): per bestfolio.app's disclosed "Golden Ratio Dual
Gate (SPY + TIP)" strategy (u/confettofetti, r/LETFs) -- read via
browser_exec after web_search DDGS/Yahoo backend TLS-errored on this
iteration's query -- a two-state daily tactical gate uses TWO separate
200-day-SMA-band hysteresis switches rather than a single trend filter:

1. A primary gate on the TRADED asset itself: turns ON when close is
   >= entry_pct above its own SMA(trend_window), turns OFF when close
   falls <= exit_pct below that SMA, and HOLDS its previous state while
   the price sits inside that dead-band (this is the "hysteresis" that
   reduces whipsaw turnover vs a naive single-line crossover).
2. A secondary "TIP canary" gate on the TIP (iShares TIPS Bond ETF) price
   relative to ITS OWN SMA(tip_trend_window), using the SAME asymmetric
   entry/exit band logic. The source's own rationale: TIP is a real-yield
   proxy, and this canary "steps the strategy out of leverage in
   inflation/rates regimes the SPY 200-SMA alone misses."
3. Long/full-exposure only when BOTH gates are simultaneously ON; flat
   otherwise (this repo is long-only per SAFETY.md, so we use plain 0/1
   exposure rather than the source's UPRO-overlay leverage-toggle
   construction, which is not implementable under our no-order-placement
   safety constraint anyway).

This is distinct from EVERY prior TIP-gated strategy in this repo:
- 2026-09-11-059/060 (GLD/TIP real-yield gate, accepted QQQ+SPY): uses a
  SINGLE-LINE (no dead-band) close>SMA crossover on TIP, not a dual
  ASYMMETRIC-BAND hysteresis switch on both TIP and the traded asset.
- 2026-09-10-027 (TIP/IEF ratio regime gate, rejected): uses a ratio of
  two bond ETFs, not TIP's own absolute-price hysteresis band.
- No prior entry combines an asymmetric-percentage-band hysteresis gate
  on the TRADED ASSET ITSELF with a second, independent hysteresis gate
  on a cross-asset canary series -- this repo's existing hysteresis
  entries (gold/silver ratio 2026-09-05-030, copper/gold ratio
  2026-09-05-032) apply hysteresis to a single cross-asset RATIO z-score,
  not to two SEPARATE percentage-band switches gated with AND logic.

Source: https://bestfolio.app/strategies (Golden Ratio Dual Gate (SPY +
TIP) strategy card, viewed 2026-09-23 via browser_exec).
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _naive_index(idx):
    return idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx


def _hysteresis_band_state(
    close: pd.Series,
    sma_window: int,
    entry_pct: float,
    exit_pct: float,
) -> pd.Series:
    """Two-line asymmetric-band hysteresis switch: ON above +entry_pct band,
    OFF below -exit_pct band, HOLD previous state inside the dead-band.
    """
    sma = close.rolling(sma_window, min_periods=max(2, sma_window // 2)).mean()
    pct_above = (close - sma) / sma

    n = len(close)
    state = np.zeros(n, dtype=bool)
    pct_vals = pct_above.to_numpy()
    prev = False
    for i in range(n):
        v = pct_vals[i]
        if np.isnan(v):
            state[i] = prev
            continue
        if v >= entry_pct:
            prev = True
        elif v <= -exit_pct:
            prev = False
        # else: hold prev
        state[i] = prev
    return pd.Series(state, index=close.index)


def _get_tip_gate(idx: pd.DatetimeIndex, tip_trend_window: int, tip_entry_pct: float, tip_exit_pct: float) -> pd.Series:
    from loaders import load_equity

    lookback_days = tip_trend_window * 2 + 60
    start = (idx.min() - pd.Timedelta(days=lookback_days)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()
    tip_close = load_equity("TIP", start, end).set_index("timestamp")["close"].sort_index()
    tip_close.index = _naive_index(tip_close.index)

    tip_gate = _hysteresis_band_state(tip_close, tip_trend_window, tip_entry_pct, tip_exit_pct)

    target_idx = _naive_index(idx)
    tip_gate = tip_gate.reindex(tip_gate.index.union(target_idx)).sort_index().ffill()
    tip_gate = tip_gate.reindex(target_idx)
    tip_gate.index = idx
    return tip_gate.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    entry_pct: float = 0.01,
    exit_pct: float = 0.01,
    tip_trend_window: int = 200,
    tip_entry_pct: float = 0.001,
    tip_exit_pct: float = 0.001,
    is_crypto: bool = False,
) -> pd.Series:
    """Dual-gate hysteresis long/flat position: own-asset band AND TIP canary band."""
    df = _prep(price_df)
    idx = df.index
    close = df["close"]

    primary_gate = _hysteresis_band_state(close, trend_window, entry_pct, exit_pct)

    if is_crypto:
        tip_gate = pd.Series(True, index=idx)
    else:
        try:
            tip_gate = _get_tip_gate(idx, tip_trend_window, tip_entry_pct, tip_exit_pct)
        except Exception:
            tip_gate = pd.Series(True, index=idx)

    position = (primary_gate.fillna(False) & tip_gate.fillna(False)).astype(int)
    position.index = idx
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

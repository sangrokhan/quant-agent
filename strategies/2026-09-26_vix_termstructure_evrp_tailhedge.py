"""Strategy: VIX Term-Structure + eVRP Tail-Hedge Overlay (SPY/VIXY blend).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-022):
Per QuantPedia's "Hedging Tail Risk with Robust VIXY Models"
(https://quantpedia.com/hedging-tail-risk-with-robust-vixy-models/,
browser_exec, own-research 29 Sep 2025, itself citing Zarattini/Mele/Aziz):
a portfolio of 80% SPY + 20% dynamically-allocated VIXY (else cash for that
slice), where the 20% VIXY slice is activated when BOTH:
  (a) expected volatility risk premium eVRP = VIX - realized_vol(SPY) <= 0
      (implied vol has compressed below realized -- volatility "underpriced"
      relative to what's actually happening, a warning sign), AND
  (b) VIX > VIX3M (short-term fear exceeds medium-term expectations, a
      term-structure inversion signaling acute stress)
Otherwise the VIXY slice sits in cash and the portfolio is effectively
100% SPY-equivalent (80% exposure + 20% cash, per the source's own
described mechanic).

The source's OWN disclosed benchmark (naive VIX>VXV alone, no eVRP) already
underperforms pure buy-and-hold SPY (Sharpe 0.38 vs 0.56) -- flagged
explicitly in the source as insufficiently effective on its own, which is
exactly why they add the eVRP refinement. This strategy tests that eVRP
refinement directly.

First VIX-term-structure + eVRP tail-hedge overlay strategy in this repo.
Adapted to the single-asset generate_returns(price_df, **params) contract:
price_df is treated as the primary equity asset (SPY); VIX/VIX3M/VIXY are
fetched internally via data/loaders.py.

Interface contract:
    generate_signals(price_df, **params) -> pd.Series ({0,1}, VIXY-hedge ON/OFF)
    generate_returns(price_df, **params) -> pd.Series (blended daily returns)
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_aux(index: pd.DatetimeIndex) -> pd.DataFrame:
    key = "vix_aux"
    if key not in _cache:
        import sys
        import os

        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
        from loaders import load_equity  # noqa: E402

        start, end = datetime(2004, 1, 1), datetime(2026, 12, 31)
        vix = load_equity("^VIX", start, end)
        vix3m = load_equity("^VIX3M", start, end)
        vixy = load_equity("VIXY", start, end)

        def _clean(df):
            df = _prep(df)
            return df["close"]

        _cache[key] = pd.DataFrame({
            "VIX": _clean(vix),
            "VIX3M": _clean(vix3m),
            "VIXY": _clean(vixy),
        })
    aux = _cache[key]
    return aux.reindex(index).ffill()


def generate_signals(
    price_df: pd.DataFrame,
    realized_vol_window: int = 21,
    vixy_weight: float = 0.20,
) -> pd.Series:
    """Return a {0,1} series: 1 = VIXY hedge slice active, 0 = cash for that slice."""
    df = _prep(price_df)
    close = df["close"]

    aux = _load_aux(close.index)
    vix, vix3m = aux["VIX"], aux["VIX3M"]

    daily_ret = close.pct_change()
    realized_vol_ann = daily_ret.rolling(realized_vol_window).std() * np.sqrt(252) * 100.0

    evrp = vix - realized_vol_ann
    term_structure_inverted = vix > vix3m

    hedge_on = ((evrp <= 0) & term_structure_inverted).fillna(False).astype(int)
    return hedge_on


def generate_returns(
    price_df: pd.DataFrame,
    realized_vol_window: int = 21,
    vixy_weight: float = 0.20,
) -> pd.Series:
    """Blended daily returns: (1-vixy_weight)*SPY + vixy_weight*VIXY when hedge is on,
    else just (1-vixy_weight)*SPY (remaining vixy_weight sits in cash, 0 return)."""
    df = _prep(price_df)
    close = df["close"]
    spy_ret = close.pct_change().fillna(0.0)

    aux = _load_aux(close.index)
    vixy_ret = aux["VIXY"].pct_change().fillna(0.0)

    hedge_on = generate_signals(price_df, realized_vol_window=realized_vol_window, vixy_weight=vixy_weight)
    # one-day lag per source's own disclosed implementation timing
    hedge_on_lagged = hedge_on.shift(1).fillna(0).astype(int)

    equity_weight = 1.0 - vixy_weight
    blended = equity_weight * spy_ret + hedge_on_lagged * vixy_weight * vixy_ret
    return blended

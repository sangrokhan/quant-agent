"""Strategy: Long SVXY (short-vol ETF) gated by a DUAL signal combining the
Volatility Risk Premium (VRP = VIX - realized vol) AND the VIX/VIX3M
term-structure slope, per Zarattini/Aziz/Mele "The Volatility Edge: A Dual
Approach For VIX ETNs Trading" (SSRN 5316487, referenced in Quantpedia's
April 2026 monthly digest; read via concretumgroup.com's public summary of
the paper this iteration -- browser_exec, since web_extract's ddgs backend
cannot fetch page content).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-13-XXX):
The source paper tests four VIX-ETN rule sets, from a constant short-vol
allocation up to a final strategy that "adapts position sizing based on two
key signals: the option-market volatility premium, and the slope of the VIX
term structure" -- explicitly a DUAL-signal design, contrasted with single
signal approaches. This repo already has two adjacent PRIOR entries that
each used exactly ONE of these two signals in isolation on a single asset:
  - 2026-09-05-044 (VRP = VIX - realized_vol regime filter) -- accepted for
    QQQ, but never applied to a volatility ETP itself.
  - 2026-09-11-071 (VIX/VIX3M term-structure-only gate on SVXY) -- REJECTED
    decisively: Sharpe 0.639, MDD 0.402 full-sample; grid confirmed the
    edge only survives in low-vol regimes (9/9 low-vol pass, 0/9 mid, 0/9
    high) -- i.e. the single term-structure gate reacts too slowly/coarsely
    to the Volmageddon-style vol spikes that occur going INTO mid/high-vol
    regimes.

This iteration's novel, testable variant: require BOTH signals favorable
before going long SVXY (long-only AND-gate, no dynamic position sizing per
SAFETY.md/this repo's long/flat convention) --
  1. Term structure in contango: VIX/VIX3M ratio <= contango_thresh (same
     mechanic as 2026-09-11-071).
  2. VRP positive: VIX - realized_vol(price_df's OWN close, rv_window) >
     vrp_threshold (same mechanic/threshold family as 2026-09-05-044, but
     applied to SVXY's own realized vol rather than QQQ's).
The economic rationale for combining them: the term-structure-only version
failed specifically because contango can persist right up to the moment
realized volatility starts spiking (the ratio lags actual price turbulence
by construction, since VIX3M is itself a smoothed longer-dated expectation).
The VRP signal computed off SVXY's/the underlying market's OWN realized vol
is a faster-reacting, contemporaneous stress detector -- once realized vol
starts climbing (even before the futures curve inverts), VRP shrinks or
turns negative and the AND-gate flips flat immediately, rather than waiting
for the ratio to cross 1.0. This is the first strategy in this repo to
combine BOTH the VRP spread AND the term-structure-ratio signals into one
AND-gated rule (distinct from either used alone).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import math
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_vix_signals(index: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series]:
    """Load ^VIX and ^VIX3M via data/loaders.py, aligned to index.

    Returns (vix_close, term_structure_ratio) both reindexed/ffilled onto
    the supplied index.
    """
    from loaders import load_equity  # noqa: E402

    start = (index.min() - pd.Timedelta(days=10)).to_pydatetime()
    end = (index.max() + pd.Timedelta(days=10)).to_pydatetime()

    vix = load_equity("^VIX", start, end)
    vix3m = load_equity("^VIX3M", start, end)

    vix = vix.set_index("timestamp")["close"] if "timestamp" in vix.columns else vix["close"]
    vix3m = vix3m.set_index("timestamp")["close"] if "timestamp" in vix3m.columns else vix3m["close"]

    vix.index = pd.to_datetime(vix.index).tz_localize(None)
    vix3m.index = pd.to_datetime(vix3m.index).tz_localize(None)

    ratio = (vix / vix3m).dropna()

    idx_naive = pd.to_datetime(index).tz_localize(None)
    vix_aligned = vix.reindex(idx_naive).ffill()
    ratio_aligned = ratio.reindex(idx_naive).ffill()
    vix_aligned.index = index
    ratio_aligned.index = index
    return vix_aligned, ratio_aligned


def _realized_vol(close: pd.Series, window: int) -> pd.Series:
    """Annualized rolling realized vol (percentage points) of the
    underlying's own daily log returns -- same construction as the accepted
    VRP strategy (2026-09-05-044)."""
    log_ret = (close / close.shift(1)).apply(
        lambda r: math.log(r) if r and r > 0 else None
    ).astype(float)
    rv = log_ret.rolling(window).std() * math.sqrt(252) * 100.0
    return rv


def generate_signals(
    price_df: pd.DataFrame,
    contango_thresh: float = 1.0,
    vrp_threshold: float = 2.0,
    rv_window: int = 20,
    min_hold_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series for SVXY.

    Long only when BOTH:
      - VIX/VIX3M ratio <= contango_thresh (contango / calm regime), AND
      - VRP = VIX - realized_vol(price_df close, rv_window) > vrp_threshold
        (implied vol meaningfully exceeds realized -- options overpricing
        turbulence, a risk-on/harvestable regime).
    Once flat due to either signal flipping unfavorable, requires
    min_hold_days consecutive favorable days before re-entering (whipsaw
    reduction, same mechanic as 2026-09-11-071).
    """
    df = _prep(price_df)
    close = df["close"]

    vix, ratio = _load_vix_signals(close.index)
    realized_vol = _realized_vol(close, rv_window)
    vrp = vix - realized_vol

    contango = (ratio <= contango_thresh).fillna(False)
    vrp_favorable = (vrp > vrp_threshold).fillna(False)
    favorable = (contango & vrp_favorable).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    favorable_streak = 0
    for i in range(len(close)):
        is_favorable = bool(favorable.iloc[i])
        if in_position:
            if not is_favorable:
                in_position = False
                favorable_streak = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if is_favorable:
                favorable_streak += 1
            else:
                favorable_streak = 0
            if favorable_streak >= min_hold_days:
                in_position = True
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

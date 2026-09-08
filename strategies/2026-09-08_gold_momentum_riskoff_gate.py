"""Strategy: Gold-Momentum Risk-Off Gate (defensive-asset early-warning filter).

Hypothesis (see knowledge_base/strategies_log.jsonl, this id):
Per Thomas Carlson, "Defense First: A Multi-Asset Tactical Model for
Adaptive Downside Protection" (2025), summarized at
https://www.quantitativo.com/p/from-defense-to-offense-a-tactical -- a
tactical model ranks defensive assets (TLT, GLD, DBC, UUP) each month by
multi-timeframe absolute momentum, allocating to whichever defensive
assets show positive momentum (monetary-instability/inflation/crisis
hedges) and falling back to equities only when ALL defenses are weak.

This repo trades a single primary equity/crypto asset rather than a
multi-asset TAA portfolio, so we adapt the core mechanism as a single-edge
RISK-OFF GATE: when GOLD (GLD) itself shows strong positive absolute
momentum (a classic monetary-instability/flight-to-safety signal per the
source's own framework), treat that as an early warning of market stress
and go flat on the primary equity/crypto asset; otherwise stay long
(assuming the primary's own trend is separately still up, via a light SMA
filter to avoid catching genuine primary-asset downtrends the gold signal
doesn't cover).

Distinct from the already-tested gold/silver RATIO regime filter
(2026-09-05-030, GLD/SLV z-score) and every other cross-asset regime
filter in this repo: this uses GLD's OWN absolute momentum (not a ratio
against another commodity, and not a level/SMA position), as a pure
risk-off circuit-breaker gate layered on top of (not instead of) the
primary asset's own trend filter -- mirroring the source's actual
"defensive assets flash warning -> reduce offense" mechanism more directly
than a ratio-based proxy would.

Signal logic
------------
- Primary trend filter: close[t] > SMA(trend_window)[t].
- Gold risk-off flag: GLD's trailing `gold_lookback`-day return exceeds
  `gold_threshold` (gold surging = risk-off warning).
- Position = 1 (long) when primary trend is up AND gold risk-off flag is
  False; 0 (flat) otherwise (either primary downtrend, or gold flashing a
  risk-off warning).
- Lagged 1 day.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_gold(start, end) -> pd.Series:
    df = load_equity("GLD", start, end)
    df = _prep(df)
    return df["close"]


def _simulate(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    gold_lookback: int = 63,
    gold_threshold: float = 0.05,
) -> pd.DataFrame:
    df = _prep(price_df)
    primary_close = df["close"]
    start, end = df.index.min(), df.index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None)

    gold_close = _load_gold(start, end)
    gold_close = gold_close.reindex(primary_close.index, method="ffill")
    gold_trail = gold_close.pct_change(gold_lookback)

    sma = primary_close.rolling(trend_window, min_periods=trend_window // 2).mean()
    primary_uptrend = primary_close > sma
    gold_risk_off = gold_trail > gold_threshold

    raw_signal = (primary_uptrend & (~gold_risk_off)).fillna(False).astype(int)
    position = raw_signal.shift(1).fillna(0).astype(int)

    daily_ret = primary_close.pct_change().fillna(0.0)
    strat_ret = position * daily_ret

    return pd.DataFrame({"position": position, "returns": strat_ret}, index=primary_close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    gold_lookback: int = 63,
    gold_threshold: float = 0.05,
) -> pd.Series:
    result = _simulate(price_df, trend_window, gold_lookback, gold_threshold)
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    gold_lookback: int = 63,
    gold_threshold: float = 0.05,
) -> pd.Series:
    result = _simulate(price_df, trend_window, gold_lookback, gold_threshold)
    return result["returns"]

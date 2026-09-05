"""Strategy: CBOE SKEW index extreme-tail-risk regime filter (equity/crypto).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-029):
The CBOE SKEW Index (SKEW = 100 - 10*S, where S is the risk-neutral
skewness of the 30-day S&P 500 log return distribution) measures how much
the market is paying for crash/tail protection -- historically ranging
100-147 (1990-2010), modal 115-117.5, per
https://ecmsource.com/volatility-skew-and-smile-explained-why-otm-puts-cost-more/
(citing the Cboe SKEW whitepaper, 2010). That source explicitly warns
SKEW is NOT meant as a standalone directional timing signal (high SKEW
appears in both calm and panicky VIX regimes) -- but this strategy tests
a narrower, mechanical claim anyway: does going flat specifically during
STATISTICALLY EXTREME SKEW readings (relative to its own trailing
history, not an absolute level) reduce drawdown/improve risk-adjusted
returns, since an abnormally-elevated tail-risk premium may still be
informative about near-term crash risk pricing even if it isn't a
reliable *directional* forecast on its own.

This is distinct from the other CBOE-volatility-index strategy in this
repo, VIX/VIX3M term-structure backwardation (2026-09-05-028, which uses
the *level* comparison across VIX maturities/contango-backwardation, not
skewness of the single-maturity smile) and from VIX-BB-breakout
(2026-09-04, which uses VIX's own level vs Bollinger Bands, not SKEW).

Signal logic
------------
- Rolling z-score of SKEW over `skew_lookback` days (mean/std of trailing
  window, not the full-history modal 115-117.5 hardcoded, so the filter
  adapts to regime drift over the multi-year backtest window).
- "Extreme tail-risk regime": SKEW z-score >= extreme_z_threshold.
- Flat while in the extreme regime (protection cost/implied crash risk
  abnormally high vs recent history); long otherwise.
- min_hold_days after a flip (either direction) to reduce whipsaw around
  the threshold, matching the recovery-window pattern used in the
  VIX/VIX3M strategy in this repo.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402

_skew_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _get_skew(start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Fetch ^SKEW close series covering [start, end], cached."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _skew_cache:
        return _skew_cache[key]

    fetch_start = datetime(max(start.year - 2, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    skew = load_equity("^SKEW", fetch_start, fetch_end)
    skew = skew.set_index(pd.to_datetime(skew["timestamp"], utc=True))["close"]
    skew = skew[~skew.index.duplicated(keep="first")].sort_index()
    _skew_cache[key] = skew
    return skew


def generate_signals(
    price_df: pd.DataFrame,
    skew_lookback: int = 252,
    extreme_z_threshold: float = 1.5,
    min_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on the SKEW regime."""
    df = _prep(price_df)
    idx = df.index

    skew_full = _get_skew(idx.min(), idx.max())
    skew = skew_full.reindex(idx, method="ffill").bfill()

    skew_mean = skew.rolling(skew_lookback, min_periods=skew_lookback // 2).mean()
    skew_std = skew.rolling(skew_lookback, min_periods=skew_lookback // 2).std()
    z = ((skew - skew_mean) / skew_std).fillna(0.0)

    extreme = z >= extreme_z_threshold

    position = pd.Series(0, index=idx, dtype=int)
    current_state = 1  # start long by default (assume normal regime)
    days_since_flip = min_hold_days  # allow immediate state at start
    for i in range(len(idx)):
        desired_state = 0 if bool(extreme.iloc[i]) else 1
        if desired_state != current_state:
            days_since_flip = 0
            current_state = desired_state
        else:
            days_since_flip += 1
        # During the min_hold cooldown right after a flip, hold the
        # PREVIOUS state one extra beat to reduce single-day whipsaw --
        # simplified here to: apply the new state immediately (flip is
        # already conservative because it's on a smoothed z-score), but
        # require min_hold_days of consecutive same-state readings before
        # trusting a flip back into a long risk state after being flat.
        if current_state == 1 and days_since_flip < min_hold_days:
            position.iloc[i] = 0
        else:
            position.iloc[i] = current_state
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

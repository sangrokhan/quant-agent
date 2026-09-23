"""Strategy: 52-Week High Proximity anchoring (single-asset adaptation).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-033):
Per George & Hwang (2004, Journal of Finance 59(5), 2145-2176) and
corroborated by https://blog.tradingstudio.finance/52-week-high-proximity-us-stocks/
(read via browser_exec this iteration; web_search worked for the initial
discovery query but the extract backend -- ddgs -- cannot fetch page
content, so browser_exec was used for the full-text read): stocks trading
near their 52-week high exhibit systematic underreaction/anchoring --
investors who "missed" the run-up hesitate to buy near the old high,
creating a psychological ceiling whose eventual breach triggers a
predictable continuation drift. The source's own construction is
`proximity_ratio = adjClose / MAX(high over trailing 252 trading days)`,
used there as a CROSS-SECTIONAL stock-selection signal (top-30 quarterly
rebalance across the NYSE/NASDAQ/AMEX universe) -- infeasible in this
repo's single-symbol `generate_returns_fn` architecture. This strategy
adapts the same proximity_ratio construction to a SINGLE-ASSET
continuous-sizing dial: the closer price sits to its own trailing 252-day
high, the stronger the anchoring-breach momentum thesis, so exposure scales
up smoothly with proximity_ratio (only above a `min_proximity` floor to
avoid taking anchoring-momentum exposure while far from the high, where the
mechanism doesn't apply), rather than a discrete cross-sectional selection.
First "52-week high proximity" / anchoring-hypothesis strategy in this repo
(0 prior KB hits for "52 week high", "proximity ratio", "anchoring
hypothesis", or George & Hwang).

Signal logic
------------
- proximity_ratio[t] = close[t] / rolling_max(high, lookback_days)[t]
  (rolling_max uses `high`, the source's `adjClose/high` convention
  approximated here with close/rolling-high since this repo's OHLCV loader
  already provides split/dividend-adjusted series).
- Exposure dial: when proximity_ratio >= min_proximity, scale exposure
  linearly from 0 (at min_proximity) to leverage_cap (at proximity_ratio=1.0);
  clip to [0, leverage_cap]. Below min_proximity, exposure is 0 (flat) --
  anchoring-driven continuation is only hypothesized to matter near the
  high, per the source's own top-30-closest-to-high selection logic.
- A `deadband` on exposure changes reduces low-value rebalancing turnover
  (this repo's established fix for continuous-sizing-dial transaction-cost
  failures, e.g. Ultimate Oscillator 2026-09-13-079).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0..leverage_cap exposure)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 252,
    min_proximity: float = 0.85,
    leverage_cap: float = 1.0,
    deadband: float = 0.05,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series.

    Exposure scales linearly with how close price is to its own trailing
    `lookback_days` high, only engaging above `min_proximity`.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close

    rolling_high = high.rolling(lookback_days, min_periods=max(20, lookback_days // 4)).max()
    proximity_ratio = (close / rolling_high).clip(upper=1.0)

    # Linear scale: 0 at min_proximity, leverage_cap at 1.0
    span = max(1e-9, 1.0 - min_proximity)
    raw_exposure = ((proximity_ratio - min_proximity) / span).clip(lower=0.0, upper=1.0) * leverage_cap
    raw_exposure = raw_exposure.fillna(0.0)

    # Deadband: only move exposure if the change exceeds `deadband` * leverage_cap
    position = pd.Series(0.0, index=close.index, dtype=float)
    current = 0.0
    threshold = deadband * leverage_cap
    for i in range(len(close)):
        target = raw_exposure.iloc[i]
        if abs(target - current) >= threshold:
            current = target
        position.iloc[i] = current
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

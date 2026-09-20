"""Strategy: Defensive Compounder leverage-tier gate (FinLab-style).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-124):
Source: https://finlab.finance/en/blog/us-low-volatility-strategy (visited
2026-09-20 via browser_exec, web_extract backend unavailable this run).

FinLab's backtest shows that applying full 2x leverage to a broad index
ETF ONLY during a simple "risk-on" regime -- close above its 200-day SMA
AND positive trailing 126-day (~6-month) return -- captures most of 2x
leverage's upside while avoiding most of its downside, because the daily
variance-drag on a daily-reset leveraged product scales with realized
variance, and realized volatility is measurably higher in risk-off periods
(source: 29.9% annualized vol on risk-off days vs 18.3% on risk-on days)
even though risk-off next-day *returns* are barely different from risk-on.
The mechanism is explicitly variance-drag avoidance, NOT return prediction.

This is distinct from prior leverage-tier strategies in this repo:
- 2026-09-18-104 (VIX-gated leverage tier): uses VIX level as the gating
  signal, substitutes a TLT hedge leg in bear regimes.
- 2026-09-18-005 (Quad-Signal majority vote): uses a >=2-of-4 vote across
  four different signal categories (long trend, medium trend, realized
  vol, return persistence), un-leveraged base asset.
This strategy uses exactly the source's own two-condition AND-gate
(200d SMA trend + 126d absolute momentum) as a binary leverage MULTIPLIER
applied directly to the underlying asset's own daily return series (no
separate hedge asset, no vote structure) -- simulating the effect of
holding 2x leverage only in the risk-on regime and unleveraged (or reduced)
exposure otherwise.

Signal logic
------------
- risk_on = close > SMA(trend_window) AND (close / close.shift(mom_window) - 1) > 0
- position exposure: leverage_on when risk_on, leverage_off when risk_off
  (both continuous multipliers applied to the underlying daily return,
  not a binary 0/1 hold/flat -- this is a leverage-tier strategy, not an
  entry/exit strategy. Always "in the market" at some exposure level.)

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (exposure multiplier
        series, NOT strictly {0,1} -- validators.check_walk_forward etc.
        just need a returns series, so generate_signals here returns the
        continuous exposure dial for transparency/paper-trading use).
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
    trend_window: int = 200,
    mom_window: int = 126,
    leverage_on: float = 2.0,
    leverage_off: float = 1.0,
) -> pd.Series:
    """Return a continuous exposure-multiplier series (leverage_on/leverage_off)."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    trend_ok = close > sma
    mom = close / close.shift(mom_window) - 1.0
    mom_ok = mom > 0.0

    risk_on = (trend_ok & mom_ok).fillna(False)
    exposure = pd.Series(leverage_off, index=close.index, dtype=float)
    exposure[risk_on] = leverage_on
    return exposure


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted (leverage-scaled) daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift exposure by 1 day: yesterday's regime determines today's leverage
    # tier (avoid look-ahead bias -- can't act on today's own close).
    strategy_ret = exposure.shift(1).fillna(kwargs.get("leverage_off", 1.0)) * daily_ret
    return strategy_ret

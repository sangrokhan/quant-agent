"""Strategy: CPPI (Constant Proportion Portfolio Insurance) with Max-Drawdown
extension, applied as a dynamic position-sizing overlay on a plain SMA trend
gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-174):
Per Quantpedia "Introduction to CPPI - Constant Proportion Portfolio
Insurance" (https://quantpedia.com/introduction-to-cppi-constant-proportion-portfolio-insurance/),
a CPPI strategy dynamically scales exposure to a risky asset based on the
"cushion" (current portfolio value minus a protective floor) times a fixed
multiplier M -- as the cushion shrinks (losses accumulate), risky exposure
is reduced proportionally, capping downside while preserving upside
convexity. The article's "Maximum Drawdown extension" variant sets the
floor as `a` (e.g. 0.8) times the portfolio's own running-max value (a
never-decreasing process), so the strategy explicitly targets keeping the
strategy's own realized max drawdown below `1 - a`.

This is a direct, source-grounded follow-up to this cron trigger's own
2026-09-08-173 (HMM regime filter) near-miss, which passed Sharpe/walk-
forward/param-sensitivity on QQQ but failed decisively on max_drawdown
(0.386) -- CPPI's max-drawdown-extension floor mechanism is designed
precisely to control that failure mode via position sizing rather than a
binary regime on/off gate.

Implementation (single-asset time-series adaptation, no explicit "safe
asset" -- unallocated capital sits in cash/0-return, standard for a
long-only vectorbt-style single-instrument backtest):
- Only trade when in an SMA(trend_window) uptrend (same base trend filter
  used by other position-sizing-overlay strategy 2026-09-08-165, isolating
  the CPPI SIZING mechanism as the novel variable, matching that strategy's
  own "isolates whether the SIZING mechanism improves risk-adjusted
  performance" framing).
- Track a shadow NAV process (starts at 1.0, compounds daily by
  weight * daily_return where weight is today's CPPI-derived exposure).
- running_max = expanding running maximum of shadow NAV.
- floor = max_drawdown_floor_pct * running_max (Max Drawdown extension).
- cushion = max(shadow_NAV - floor, 0).
- risky_weight = clip(multiplier * cushion / shadow_NAV, 0, leverage_cap)
  when in an uptrend; 0 otherwise.

First CPPI / dynamic-floor-based drawdown-control position-sizing entry in
this repo -- distinct from the plain inverse-realized-vol-targeting overlay
(2026-09-08-165, sizing driven by trailing volatility, not a path-dependent
running-max drawdown floor).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series (weight,
        NOT strictly {0,1} -- returns the continuous CPPI exposure weight,
        consistent with how 2026-09-08-165's vol-targeting overlay also
        returns a continuous sizing series rather than a binary position.)
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
    multiplier: float = 3.0,
    max_drawdown_floor_pct: float = 0.9,
    leverage_cap: float = 1.0,
    rebalance_threshold: float = 0.0,
) -> pd.Series:
    """Return the CPPI exposure weight series (continuous, in [0, leverage_cap]).

    ``rebalance_threshold`` (added in the 2026-09-08-175 refinement of
    near-miss 2026-09-08-174): only actually CHANGE the held weight when the
    freshly-computed CPPI target weight differs from the currently-held
    weight by more than this fraction (e.g. 0.1 = 10 percentage points).
    Otherwise keep holding the prior weight -- this is a standard "no-trade
    band" used to cut rebalancing-driven transaction costs for continuous
    sizing strategies, applied on top of the identical Max-Drawdown-extension
    CPPI mechanism from 2026-09-08-174 (unchanged when rebalance_threshold=0,
    matching that entry's default behavior exactly for backward comparability).
    """
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    uptrend = close > sma

    daily_ret = close.pct_change().fillna(0.0)

    weight = pd.Series(0.0, index=close.index)
    shadow_nav = 1.0
    running_max = 1.0
    held_weight = 0.0

    for i in range(len(close)):
        floor = max_drawdown_floor_pct * running_max
        cushion = max(shadow_nav - floor, 0.0)
        raw_weight = (multiplier * cushion / shadow_nav) if shadow_nav > 0 else 0.0
        target_w = min(max(raw_weight, 0.0), leverage_cap)
        if not bool(uptrend.iloc[i]):
            target_w = 0.0

        if abs(target_w - held_weight) > rebalance_threshold:
            held_weight = target_w
        weight.iloc[i] = held_weight

        # Compound the shadow NAV forward using the weight decided at close
        # of day i-1 applied to day i's realized return (no look-ahead).
        if i > 0:
            shadow_nav = shadow_nav * (1.0 + weight.iloc[i - 1] * daily_ret.iloc[i])
            running_max = max(running_max, shadow_nav)

    return weight


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    Weight decided using info through close of day t-1 is applied to day t's
    return (shift by 1, same no-lookahead convention as every other
    strategy in this repo).
    """
    df = _prep(price_df)
    close = df["close"]
    weight = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (weight.shift(1).fillna(0.0) * daily_ret)
    return strategy_ret

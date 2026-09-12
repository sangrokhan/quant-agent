"""Strategy: "Poor Man's Trend Program" continuous vol-scaled trend exposure
(single-lookback z-scored-return sizing).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-13-XXX):
Per https://beyondpassive.substack.com/p/the-missing-asset-120-years-of-global
(read via browser_exec this iteration), a prior article in this Substack
series built a "poor man's trend program" tested on 120 years of annual
US/global stocks-bonds-gold data: signal = last period's total return
divided by its own trailing long-horizon volatility, clipped to [-1, 1];
exposure = 0.5 + 0.5*signal (so a strong period keeps full exposure, a
flat period gives half exposure, and a bad period removes exposure
entirely). No leverage, no shorting. Source's own finding: this
continuous-exposure trend rule cut maximum drawdown roughly in half (59%
-> 17% in the 120-year annual global multi-asset test; also validated
separately on 1968-2020 daily US data with multiple lookbacks combined)
while holding total return roughly flat, with the benefit concentrated in
"stagflation" (falling growth + rising inflation) regimes -- a
PRICE-ONLY rule that reduces exposure specifically when needed without
ever being told what regime it is in.

Adapted here to this repo's daily-bar single-asset contract: signal =
trailing lookback_days return, annualized and divided by its own trailing
vol_window-day annualized realized volatility (a return-to-risk /
"Sharpe-like" z-score), clipped to [-1, 1]; exposure =
base_weight + base_weight*signal (base_weight=0.5 matches source's
1/3*(0.5+0.5*sig) sleeve construction scaled to a single-asset full-weight
convention of 1.0 max). This is the first continuous-exposure (not 0/1
binary) sizing rule in this repo based on a clipped return/vol z-score of
the asset's OWN trailing performance (distinct from the already-accepted
inverse-vol-TARGETING overlay 2026-09-08-165, which scales inversely by
volatility alone with no return/direction signal, and from the
already-tested percentile/quantile-based position-sizing entries).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  (continuous [0,1] weight series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import math

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
    vol_window: int = 756,
    base_weight: float = 0.5,
) -> pd.Series:
    """Return a continuous [0, 2*base_weight] weight series (clipped to
    [0,1] for a long-only, no-leverage convention matching the source's
    "no leverage, no shorting" rule).

    signal = trailing lookback_days annualized return / trailing
             vol_window-day annualized realized volatility, clipped to
             [-1, 1].
    weight = base_weight + base_weight * signal, clipped to [0, 1].
    """
    df = _prep(price_df)
    close = df["close"]

    trailing_ret = close.pct_change(lookback_days)
    annualization_factor = 252.0 / lookback_days
    annualized_ret = trailing_ret * annualization_factor

    daily_log_ret = (close / close.shift(1)).apply(
        lambda r: math.log(r) if r and r > 0 else None
    ).astype(float)
    trailing_vol = daily_log_ret.rolling(vol_window).std() * math.sqrt(252)

    signal = (annualized_ret / trailing_vol).clip(-1.0, 1.0)
    weight = (base_weight + base_weight * signal).clip(0.0, 1.0)
    weight = weight.fillna(0.0)
    return weight


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    weight = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = weight.shift(1).fillna(0) * daily_ret
    return strategy_ret

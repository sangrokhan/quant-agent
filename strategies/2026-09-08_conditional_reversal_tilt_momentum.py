"""Strategy: Conditional Reversal-Tilted Momentum (winners glide, losers stumble).

Hypothesis (see knowledge_base/strategies_log.jsonl, this id):
Per "Winners Glide, Losers Stumble: A Behavioral Reversal Tilt to Momentum"
(summarized in Quantitativo Weekly #2,
https://www.quantitativo.com/p/quantitativo-weekly-4f8), classic 12-1
momentum (M) can be sharpened with a zero-parameter, exact-identity tweak:
B = (1 + r) * M, where r is the asset's own gross return over the most
recent month. The source's cross-sectional-stock finding is that winners
trend up smoothly while losers fall in fits and starts punctuated by
fading rebounds -- multiplying by (1+r) shorts/de-weights rebounded losers
harder than still-falling ones, improving skewness and mitigating momentum
crashes (source's own numbers: Sharpe 0.38 -> 0.78, skew 3.68 -> -2.73
becomes the OPPOSITE sign meaning the crash-tail risk flips favorable).

This repo trades single index ETFs / crypto majors time-series, not a
cross-sectional stock universe, so we adapt B as a TIME-SERIES absolute
momentum signal instead of a cross-sectional ranking: go long the asset
when its own B score (using its own 12-1 momentum and its own last-month
return) is positive and above `b_threshold`, flat otherwise. This is the
natural single-asset analog of the paper's exact multiplicative identity
applied to the asset's own history rather than a relative rank across
many stocks.

Distinct from every prior momentum entry in this repo (e.g. 2026-09-03-012
plain 12-month TSMOM+SMA-filter, 2026-09-03 45d/90d momentum variants,
2026-09-04-097 dual-momentum rotation): none of those multiply the
momentum score by (1 + last-month return) -- this is the first entry to
implement that specific reversal-tilt / conditional-reversal mechanism.

Signal logic
------------
- 12-1 momentum: M(t) = close[t - skip_days] / close[t - lookback_days] - 1
  (skips the most recent `skip_days` trading days, per the classic 12-1
  convention -- lookback_days default 252, skip_days default 21).
- Last-month gross return: r(t) = close[t] / close[t - skip_days] - 1.
- B(t) = (1 + r(t)) * M(t).
- Position = 1 (long) when B(t) > b_threshold, else 0 (flat).
- Lagged 1 day (decision on day t's close, applied starting day t+1).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _simulate(
    price_df: pd.DataFrame,
    lookback_days: int = 252,
    skip_days: int = 21,
    b_threshold: float = 0.0,
) -> pd.DataFrame:
    df = _prep(price_df)
    close = df["close"]

    momentum_12_1 = close.shift(skip_days) / close.shift(lookback_days) - 1.0
    last_month_ret = close / close.shift(skip_days) - 1.0
    b_score = (1.0 + last_month_ret) * momentum_12_1

    raw_signal = (b_score > b_threshold).astype(int)
    position = raw_signal.shift(1).fillna(0).astype(int)

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position * daily_ret

    return pd.DataFrame({"position": position, "returns": strat_ret}, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 252,
    skip_days: int = 21,
    b_threshold: float = 0.0,
) -> pd.Series:
    result = _simulate(price_df, lookback_days, skip_days, b_threshold)
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    lookback_days: int = 252,
    skip_days: int = 21,
    b_threshold: float = 0.0,
) -> pd.Series:
    result = _simulate(price_df, lookback_days, skip_days, b_threshold)
    return result["returns"]

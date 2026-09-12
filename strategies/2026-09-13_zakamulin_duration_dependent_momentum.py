"""Strategy: Zakamulin/Giner "Optimal Trend Following" duration-dependent
monthly momentum indicator.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-13-XXX):
Per Zakamulin & Giner's "Optimal Trend Following Rules in Two-State
Regime-Switching Models" (summarized by AllocateSmartly,
https://allocatesmartly.com/zakamulins-optimal-trend-following/, read via
browser_exec this iteration -- alphaarchitect.com's own page is
Cloudflare-blocked and web_extract's ddgs backend cannot fetch page
content), a "semi-Markov switching model" fit to 124 years of market data
finds the OPTIMAL trend-following indicator is NOT a simple moving average
or 12-month momentum, but a non-monotonic weighting of past monthly
returns: returns from the recent past (lag <= ~8 months) get POSITIVE
weight (short-term momentum continues), while returns from the
intermediate past (lag ~10-30 months) get NEGATIVE weight -- because the
longer a regime (bull/bear) has persisted, the higher the probability it
is about to end ("duration dependence"). Source's own disclosed monthly
decision rule: "At the close on the last trading day of each month,
calculate the result for the optimal trend-following indicator. If the
indicator value is positive, go long..., otherwise go to cash."

This repo cannot reproduce the exact SMSM-fitted weight coefficients (not
numerically disclosed in the source, only shown as a qualitative
orange-vs-blue curve chart), but the qualitative shape described --
positive weight on short lags, negative weight on intermediate lags -- is
concrete and testable as a simplified two-term approximation:

    indicator = mean(monthly_returns[1..short_lag_months])
              - mean(monthly_returns[short_lag_months+1..long_lag_months])

i.e. recent short-term momentum MINUS intermediate-term momentum (the
"duration dependence" contrarian-to-persistence term). Long when indicator
> 0, cash otherwise, decided/held monthly per the source's own rule. First
strategy in this repo to combine short-term momentum POSITIVELY with
intermediate-term momentum NEGATIVELY in a single duration-dependent
signal (distinct from plain 12-1 momentum, dual momentum, or any prior
single-lag momentum/moving-average construction).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    short_lag_months: int = 8,
    long_lag_months: int = 24,
) -> pd.Series:
    """Return a {0,1} long/flat position series, decided once per month
    (last trading day of each month) per Zakamulin/Giner's disclosed
    decision rule, held constant through the following month.

    indicator = mean(monthly_return[t-1 .. t-short_lag_months])
              - mean(monthly_return[t-short_lag_months-1 .. t-long_lag_months])
    Long (1) when indicator > 0, flat (0) otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    # Resample to month-end closes, compute monthly returns.
    monthly_close = close.resample("ME").last().dropna()
    monthly_ret = monthly_close.pct_change()

    indicator = pd.Series(index=monthly_ret.index, dtype=float)
    for i in range(len(monthly_ret)):
        if i < long_lag_months:
            indicator.iloc[i] = float("nan")
            continue
        recent = monthly_ret.iloc[i - short_lag_months : i]
        intermediate = monthly_ret.iloc[i - long_lag_months : i - short_lag_months]
        if len(recent) == 0 or len(intermediate) == 0:
            indicator.iloc[i] = float("nan")
            continue
        indicator.iloc[i] = recent.mean() - intermediate.mean()

    monthly_position = (indicator > 0).astype(int)
    monthly_position = monthly_position.reindex(monthly_ret.index).fillna(0).astype(int)

    # Decision made at month-end close applies to the FOLLOWING month (shift
    # by one month-end period) to avoid look-ahead, then broadcast to daily
    # bars by forward-filling across the daily index.
    monthly_position_shifted = monthly_position.shift(1).fillna(0).astype(int)

    position = monthly_position_shifted.reindex(close.index, method="ffill").fillna(0).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

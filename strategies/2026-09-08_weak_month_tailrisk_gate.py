"""Strategy: Weak-Prior-Month Downside-Tail-Risk Gate (market-state similarity analog).

Hypothesis (see knowledge_base/strategies_log.jsonl, this id):
Per Valeriy Zakamulin, "Industry Rotation Using Market-State Similarity"
(2026), summarized in Quantitativo Weekly #4
(https://www.quantitativo.com/p/quantitativo-weekly-4): a weak market month
predicts a WORSE LEFT TAIL (downside risk), not necessarily a worse
average/median outcome, for the following month -- this signal is nearly
invisible to standard OLS regressions (which look at conditional means)
but shows up clearly in quantile regressions of the downside tail. The
source's own strategy: summarize the market with one number (standardized
market excess return), find historically similar states, and rotate
away from what performed badly after those states. Its payoff in the
source is specifically DEFENSIVE: Sharpe rises modestly (0.56->0.71) but
max drawdown is roughly HALVED (54%->26%) and volatility drops -- a
risk-reduction story, not a return-maximization one.

This repo trades a single primary asset, so we adapt the core "market
state similarity -> downside tail risk" finding as a single-asset
TS gate: classify the trailing month's return into a percentile bucket
against its own trailing history; when that bucket is in the WEAK tail
(bottom `weak_percentile`), treat the following period as elevated
downside-tail-risk and go flat, regardless of the primary's own trend
status; otherwise, follow a standard SMA trend filter. This differs from
every prior regime-filter entry in this repo (MAX-effect 2026-09-06-162,
ATR-percentile 2026-09-06-163, valuation-boundary 2026-09-08-145): those
gate on volatility/return EXTREMITY OF EITHER SIGN or long-term price-level
deviation; here specifically only WEAK (negative) prior-month states
trigger the defensive gate, mirroring the source paper's asymmetric
downside-tail finding (a strong prior month does NOT trigger any gate).

Signal logic
------------
- Prior-month return: r(t) = close[t]/close[t-month_days] - 1.
- Percentile rank of r(t) against its own trailing `lookback_days`-day
  history (causal, no lookahead).
- Weak-state flag: percentile_rank(r(t)) <= weak_percentile.
- SMA trend filter: close[t] > SMA(trend_window)[t].
- Position = 1 (long) when trend filter is up AND weak-state flag is
  False; 0 (flat) otherwise (either downtrend, or a weak-prior-month
  downside-tail-risk state).
- Lagged 1 day.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rolling_percentile_rank(values: np.ndarray, lookback: int, min_periods: int) -> np.ndarray:
    n = len(values)
    out = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(values[i]):
            continue
        lo = max(0, i - lookback + 1)
        window = values[lo : i + 1]
        window = window[~np.isnan(window)]
        if len(window) < min_periods:
            continue
        out[i] = (window <= values[i]).sum() / len(window)
    return out


def _simulate(
    price_df: pd.DataFrame,
    month_days: int = 21,
    lookback_days: int = 756,
    weak_percentile: float = 0.2,
    trend_window: int = 100,
) -> pd.DataFrame:
    df = _prep(price_df)
    close = df["close"]

    prior_month_ret = close.pct_change(month_days)
    min_periods = max(20, lookback_days // 4)
    pct_rank = pd.Series(
        _rolling_percentile_rank(prior_month_ret.to_numpy(dtype=float), lookback_days, min_periods),
        index=close.index,
    )
    weak_state = pct_rank <= weak_percentile

    sma = close.rolling(trend_window, min_periods=trend_window // 2).mean()
    uptrend = close > sma

    raw_signal = (uptrend & (~weak_state)).fillna(False).astype(int)
    position = raw_signal.shift(1).fillna(0).astype(int)

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position * daily_ret

    return pd.DataFrame({"position": position, "returns": strat_ret}, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    month_days: int = 21,
    lookback_days: int = 756,
    weak_percentile: float = 0.2,
    trend_window: int = 100,
) -> pd.Series:
    result = _simulate(price_df, month_days, lookback_days, weak_percentile, trend_window)
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    month_days: int = 21,
    lookback_days: int = 756,
    weak_percentile: float = 0.2,
    trend_window: int = 100,
) -> pd.Series:
    result = _simulate(price_df, month_days, lookback_days, weak_percentile, trend_window)
    return result["returns"]

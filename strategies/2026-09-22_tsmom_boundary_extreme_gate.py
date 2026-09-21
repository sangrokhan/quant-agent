"""Strategy: 12-month time-series absolute momentum, gated OFF when the
trailing 12-month return itself is at an extreme relative to its own
rolling historical distribution (a single-price-series proxy for the
"valuation boundary" effect).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-037):
Per Quantpedia's summary of Suominen & Hjalmarsson (2026), "Boundaries of
Time Series Momentum" (https://quantpedia.com/boundaries-of-time-series-momentum/,
SSRN https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6867878, read via
browser_exec Google SERP -> Quantpedia blog directly this iteration --
web_search DDGS backend TLS-erroring on all queries attempted): "equity
market time-series momentum performs well in mid-valuation regimes, but
breaks down near historical valuation extremes... large absolute 12-month
returns negatively predict momentum returns." The paper's own valuation
anchors (Shiller CAPE, dividend yield, term-spread moving averages) are not
available via this repo's data/loaders.py (single-symbol OHLCV only, no
macro/fundamental data source -- the same feasibility constraint already
documented for McClellan/Zweig-Breadth/MVRV-family rejections). However,
the paper's own headline mechanical finding -- "large absolute 12-month
returns negatively predict momentum returns" -- is directly testable using
ONLY the price series itself, without needing CAPE/dividend-yield data: we
operationalize "valuation extreme" as the trailing 12-month return's own
magnitude being in the tail (top/bottom `extreme_pctile`) of its OWN
rolling historical distribution over the past `lookback_years` years. This
differs from every mean-reversion/regime-filter construction previously
tested in this repo, which all gate on REALIZED-VOLATILITY percentiles
(e.g. 2026-09-03_bb_meanrev_qqq_volregime.py and its many descendants), not
on the momentum SIGNAL'S OWN return-magnitude percentile -- i.e. this fades
momentum specifically when momentum's own recent performance has been
unusually large in either direction, matching the paper's asymmetric
finding ("regardless of whether valuations are extremely high or low, and
regardless of whether the prevailing momentum signal is positive or
negative").

Distinct from this repo's existing 12-month TSMOM strategy
(2026-09-03_tsmom_12m_monthly_rebalance.py, id 2026-09-03-012, rejected)
which uses only an unconditional 200-day SMA trend co-filter with no
extreme-return gate at all.

Signal logic
------------
- Trailing 252-trading-day (~12mo) return: r(t) = close[t]/close[t-252] - 1.
- Extremeness: rolling percentile RANK of |r(t)| against its own trailing
  `lookback_years`*252-day history (self-referential, no external data).
- Boundary state: extreme = percentile_rank(|r(t)|) >= extreme_pctile
  (e.g. 90 -> top decile of its own trailing distribution).
- Position: long (1) iff r(t) > 0 AND NOT extreme; flat (0) otherwise
  (both when momentum is negative and when momentum is positive-but-
  extreme, per the paper's symmetric breakdown finding).
- Evaluated and rebalanced MONTHLY (same monthly-rebalance convention as
  the existing 12-month TSMOM strategy, for consistency/comparability).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1}
    generate_returns(price_df, **params) -> pd.Series daily strategy returns
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
    lookback_years: int = 5,
    extreme_pctile: float = 90.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series: 12m absolute momentum,
    gated OFF when |trailing 12m return| is at an extreme percentile of its
    own rolling historical distribution. Evaluated/rebalanced monthly.
    """
    df = _prep(price_df)
    close = df["close"]

    trailing_return = close / close.shift(lookback_days) - 1.0
    abs_return = trailing_return.abs()

    window = max(lookback_years * 252, lookback_days + 20)
    # Rolling percentile rank of the current |return| within its own
    # trailing `window`-day history (0-100 scale), self-referential proxy
    # for "near a historical extreme" since this repo has no CAPE/dividend
    # yield/term-spread data source.
    pct_rank = abs_return.rolling(window, min_periods=max(60, lookback_days)).apply(
        lambda x: (x < x[-1]).sum() / (len(x) - 1) * 100.0 if len(x) > 1 else 50.0,
        raw=True,
    )

    extreme = (pct_rank >= extreme_pctile).fillna(False)
    momentum_positive = (trailing_return > 0).fillna(False)

    raw_daily_signal = momentum_positive & (~extreme)

    # Monthly rebalance: sample on the last trading day of each month, hold
    # the decision fixed through the following month (same convention as
    # strategies/2026-09-03_tsmom_12m_monthly_rebalance.py).
    month_end_signal = raw_daily_signal.resample("ME").last()
    monthly_position = month_end_signal.reindex(
        pd.date_range(month_end_signal.index.min(), close.index.max(), freq="D")
    ).ffill()
    position = monthly_position.reindex(close.index, method="ffill").fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret

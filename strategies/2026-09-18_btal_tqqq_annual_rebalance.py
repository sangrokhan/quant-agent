"""Strategy: 2-ETF Anti-Beta / Leveraged-Nasdaq Annual Rebalance (BTAL + TQQQ).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-100):
Per quantifiedstrategies.com's "A Simple 2-ETF Strategy That Outperforms the
Nasdaq" (https://www.quantifiedstrategies.com/a-simple-2-etf-strategy-that-outperforms-the-nasdaq/,
crediting @thechartist on X): a static-weight portfolio of BTAL (an
anti-beta / market-neutral-short-beta ETF, used as a low-correlation hedge)
and TQQQ (3x leveraged Nasdaq-100) rebalanced only once a year (first
trading day of January) has outperformed QQQ/Nasdaq since 2012, with CAGR
18% and max drawdown 28% (source's own headline weights: 67% BTAL / 33%
TQQQ). Source's own rationale: infrequent rebalancing avoids "volatility
drag" from repeatedly buying back into TQQQ after every leveraged-ETF
whipsaw, letting the portfolio ride long-term uptrends while BTAL cushions
drawdowns during turmoil.

First fixed-weight, buy-and-hold-with-periodic-rebalance TWO-ASSET PORTFOLIO
strategy in this repo (as opposed to every prior single-instrument
signal-based long/flat strategy). Distinct from the only prior TQQQ pairing
in this repo (2026-09-11-070, TQQQ/TMF 50/50 with a -20% single-day crash
filter to IEF -- a risk-parity pair with an active crash escape hatch, no
anti-beta ETF, bimonthly not annual rebalance). This strategy has NO crash
filter and NO signal logic at all -- pure static-weight buy-and-hold with a
periodic rebalance-back-to-target-weights mechanism, closer to a "portfolio"
than a "signal strategy", but implemented here via the same
generate_signals/generate_returns keyword contract by treating "weight" as
a continuous position size rather than a discrete 0/1 flag.

Signal logic
------------
- Not a 0/1 flip -- constant target weight in TQQQ (`tqqq_weight`, default
  0.33) with the remainder (`1 - tqqq_weight`) implicitly in BTAL.
- `generate_signals` returns the (constant, non-binary) TQQQ target weight
  series -- required to be interpretable by the harness as "how much
  exposure", even though it isn't a strict {0,1} flag (this repo's
  portfolio-of-two-assets strategies, e.g. `eth_btc_relative_strength_rotation.py`
  precedent, also return continuous weights rather than a hard 0/1 flag).
- `generate_returns` computes the ACTUAL two-asset portfolio return: each
  bar, blend BTAL and TQQQ daily returns at the target weights, and simulate
  an annual rebalance (weights reset to target on the first trading day of
  each January; between rebalances the weights drift with relative
  performance, matching a real fixed-income-style buy-and-hold-with-annual-
  rebalance portfolio, not a return that magically stays at fixed weight
  every single day like a synthetic constant-mix index).
- `price_df` here is expected to be TQQQ's own price frame (for interface
  compatibility with the grid-test harness's single-symbol convention);
  BTAL's price series is fetched internally via `data/loaders.py::load_equity`
  bounded to the same date range as `price_df`.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (TQQQ target weight, not strict 0/1)
    generate_returns(price_df, **params) -> pd.Series  (daily blended portfolio returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_btal_close(index: pd.DatetimeIndex) -> pd.Series:
    """Fetch BTAL close series aligned (ffilled) to the given index."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    btal_df = load_equity("BTAL", start, end)
    btal_df = _prep(btal_df)
    aligned = btal_df["close"].reindex(index, method="ffill").bfill()
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    tqqq_weight: float = 0.33,
    rebalance_freq: str = "Y",
) -> pd.Series:
    """Return the (constant) target TQQQ weight as a series aligned to price_df's index.

    Not a strict {0,1} flag -- this is a fixed-weight two-asset portfolio,
    so the "signal" is the target allocation fraction in TQQQ (BTAL gets
    the remainder). Kept constant since the strategy's own edge (per the
    source) comes from NOT actively trading it.
    """
    df = _prep(price_df)
    return pd.Series(tqqq_weight, index=df.index, dtype=float)


def generate_returns(
    price_df: pd.DataFrame,
    tqqq_weight: float = 0.33,
    rebalance_freq: str = "Y",
) -> pd.Series:
    """Daily blended BTAL/TQQQ portfolio returns with periodic rebalancing.

    `rebalance_freq`: pandas offset alias understood by `Series.resample`
    (default "A" = annual, first trading day of each new year -- matches
    source's "first trading day of January" rule; "Q" for quarterly per the
    source's own note that quarterly vs annual doesn't change results much).
    """
    df = _prep(price_df)
    tqqq_close = df["close"]
    btal_close = _get_btal_close(tqqq_close.index)

    tqqq_ret = tqqq_close.pct_change().fillna(0.0)
    btal_ret = btal_close.pct_change().fillna(0.0)

    n = len(tqqq_ret)
    idx = tqqq_ret.index
    # Determine rebalance dates: first trading day of each period.
    period_labels = idx.to_period(rebalance_freq)
    is_rebalance_day = pd.Series(period_labels, index=idx).ne(pd.Series(period_labels, index=idx).shift(1))
    is_rebalance_day.iloc[0] = True

    w_tqqq = tqqq_weight
    w_btal = 1.0 - tqqq_weight
    portfolio_ret = pd.Series(0.0, index=idx)

    for i in range(n):
        if is_rebalance_day.iloc[i] and i > 0:
            w_tqqq = tqqq_weight
            w_btal = 1.0 - tqqq_weight
        r_t = tqqq_ret.iloc[i]
        r_b = btal_ret.iloc[i]
        port_r = w_tqqq * r_t + w_btal * r_b
        portfolio_ret.iloc[i] = port_r
        # drift weights forward with relative performance until next rebalance
        new_w_tqqq = w_tqqq * (1 + r_t)
        new_w_btal = w_btal * (1 + r_b)
        total = new_w_tqqq + new_w_btal
        if total > 0:
            w_tqqq = new_w_tqqq / total
            w_btal = new_w_btal / total

    return portfolio_ret

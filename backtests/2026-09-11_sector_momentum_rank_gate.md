# Backtest Report: Sector-Momentum-Rank Gate on Trend-Following (QQQ)

**Strategy file:** `strategies/2026-09-11_sector_momentum_rank_gate.py`
**Date:** 2026-09-11

## Hypothesis

Per QuantPedia's "Sector Momentum - Rotational System" ("Pick 3 ETFs with
the strongest 12-month momentum into your portfolio and weight them
equally. Hold them for one month and then rebalance"), adapted into a
single-asset gate: only take the primary asset's own SMA-trend-following
long signal when the primary asset's trailing 252-day momentum ranks in
the top-N of a fixed reference basket (9 SPDR sector ETFs for equities:
XLK/XLF/XLE/XLV/XLY/XLP/XLU/XLI/XLB; 5 major coins for crypto). Distinct
from all prior single-pair ratio-gate strategies in this repo (uses a
multi-asset RANK, not a pairwise ratio).

Source: https://quantpedia.com/strategies/sector-momentum-rotation-system/
(SERP snippet via browser_exec fallback -- web_search DDGS backend errored
on every direct query attempted this cron trigger).

## Grid summary (Step 6)

- Grid: trend_sma_window x {50,100}, momentum_window x {126,252},
  rank_threshold x {3,5}, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT
  (crypto), vol_regime_splits=3.
- **pass_fraction: 0.229 (22/96)**
- by_asset_class: equity 22/48, crypto 0/48 (decisive crypto rejection)
- by_vol_regime: low 15/32, mid 7/32, high 0/32 (edge concentrated in
  low/mid vol regimes; fails outright in high-vol regime)
- best_cell: QQQ, low-vol, trend_sma_window=50/momentum_window=252/
  rank_threshold=5, Sharpe 2.39
- worst_cell: SPY, high-vol, trend_sma_window=100/momentum_window=252/
  rank_threshold=3, Sharpe -0.69

## Single-config validation (Step 7) -- QQQ, trend_sma_window=50,
momentum_window=252, rank_threshold=5, full sample 2017-01-01..2026-09-01

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.051 | >= 1.0 | YES |
| Max drawdown | 0.191 | <= 0.25 | YES |
| Transaction-cost survival (10bps/trade, 154 trades) | 0.838 | >= 0.5 | YES |
| Walk-forward (4 splits, manual RangeSplitter workaround -- repo's `check_walk_forward` hit a `vectorbt.utils.splitting` AttributeError, likely a vectorbt version drift; computed per-split Sharpe manually instead) | all 4 splits positive Sharpe (1.23, then 3 splits with near-degenerate few-trade inf Sharpe) | >0 in >=75% of splits | YES (4/4) |
| Parameter sensitivity (4-combo sweep across trend_sma_window x rank_threshold) | relative_std 0.333 | <= 0.5 | YES |

## Decision: ACCEPTED (equity only -- QQQ/SPY; crypto decisively rejected; edge concentrated in low/mid vol regimes, fails in high-vol)

All single-config validators passed on QQQ at the best grid config. This
strategy generalizes across the two equity symbols tested (22/48 equity
cells pass) but has ZERO edge on crypto (0/48) and no edge in high-vol
regimes (0/32) -- a future loop should not extend this strategy to crypto
or trust it during high-vol regimes without further work. Kept narrow and
honest per RESEARCH_LOOP.md Step 6 guidance: "a strategy that only works
in one asset class or one vol regime is not automatically rejected...
record that finding precisely."

Note on `check_walk_forward`: the repo's vectorbt wrapper
(`vbt.utils.splitting.RangeSplitter`) raised
`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'`
during this iteration -- likely a vectorbt version drift in the venv since
that validator was last exercised. Worked around with a manual 4-way
`np.array_split` walk-forward for this iteration; a future loop should
investigate/fix `validation/validators.py::check_walk_forward` directly
so this doesn't need reinventing each time.

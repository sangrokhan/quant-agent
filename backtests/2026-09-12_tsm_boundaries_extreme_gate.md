# Backtest Report: 12-Month TSM Gated by Trailing-Return Extreme Proxy (Boundaries adaptation)

**Strategy file:** `strategies/2026-09-12_tsm_boundaries_extreme_gate.py`
**Date:** 2026-09-12

## Hypothesis

Per Suominen & Hjalmarsson's "Boundaries of Time Series Momentum" (SSRN
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6867878, via Quantpedia
https://quantpedia.com/boundaries-of-time-series-momentum/): 12-month
equity time-series momentum works in mid-valuation regimes but breaks down
near historical valuation extremes (CAPE, dividend yield, term spread).
Since exact valuation data isn't obtainable via this repo's OHLCV-only
loaders, this strategy substitutes a same-asset price-based proxy: gate
standard monthly-rebalanced 12-month absolute momentum OFF when the
trailing 12-month return itself sits at a historical rolling-percentile
extreme.

## Grid test (Step 6) — `grid_result_tsm_boundaries.json`

Grid: `pct_lo ∈ {0.10,0.15,0.20}`, `pct_hi ∈ {0.80,0.85,0.90}` × symbols
{QQQ, SPY, BTC/USDT, ETH/USDT} × vol regime terciles, 2015-01-01 to
2026-09-01. 108 total cells.

- **pass_fraction: 0.1667** (18/108)
- by_asset_class: equity 18/54, **crypto 0/54** (decisive fail)
- by_vol_regime: **low 18/36, mid 0/36, high 0/36** — passes ONLY in
  low-vol regime, completely fails elsewhere
- best_cell: QQQ, `pct_lo=0.10, pct_hi=0.80`, low-vol, Sharpe 1.91
- worst_cell: ETH/USDT, `pct_lo=0.20, pct_hi=0.80`, low-vol, Sharpe -0.13

## Full-sample sweep (2015-2026)

| Symbol | (0.10,0.80) | (0.15,0.85) | (0.20,0.80) | (0.10,0.90) |
|---|---|---|---|---|
| SPY | 0.464 | 0.425 | 0.421 | 0.513 |
| QQQ | 0.348 | 0.347 | 0.312 | 0.563 |

All configurations produce full-sample Sharpe well below the 1.0
threshold for both symbols -- the low-vol-tercile grid promise (Sharpe up
to 1.91) does not translate at all to the full sample.

## Decision

**REJECT for all symbols/asset classes.** The price-based proxy for the
paper's valuation-extreme "Boundaries" variable is too blunt: gating out
extreme-return regimes alone (without the paper's actual macro-valuation
context) removes some bad periods but also strips out enough of the good
trend-following periods that overall Sharpe stays low (0.3-0.6 range) on
both SPY and QQQ full-sample. Crypto rejected decisively (0/54). This
result suggests the paper's core insight likely requires genuine external
valuation data (CAPE/dividend yield/term spread) to work as described,
not a same-asset price-only proxy -- a feasibility-blocked follow-up
worth noting for a future loop if a fundamentals data source is ever
added.

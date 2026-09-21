# TSMOM Boundary Extreme Gate — Backtest Report

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_tsmom_boundary_extreme_gate.py`
**KB id:** 2026-09-22-037

## Hypothesis

Per Quantpedia's summary of Suominen & Hjalmarsson (2026), "Boundaries of
Time Series Momentum" (https://quantpedia.com/boundaries-of-time-series-momentum/,
SSRN https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6867878, read via
browser_exec Google SERP → Quantpedia blog this iteration — web_search
DDGS backend TLS-erroring on all queries): equity time-series momentum
breaks down/reverses near historical valuation extremes (CAPE, dividend
yield, term spread). Since this repo has no macro/fundamental data source,
operationalized as a self-referential proxy: gate the existing 12-month
absolute-momentum signal (2026-09-03_tsmom_12m_monthly_rebalance.py) OFF
when the trailing-12m return's own magnitude is at an extreme percentile
(top decile) of its own rolling 3-5yr history.

## Grid test (Step 6)

`extreme_pctile` in {80, 90} x `lookback_years` in {3, 5}, symbols
{equity: QQQ, SPY; crypto: BTC/USDT, ETH/USDT}, vol_regime_splits=3.

- Total cells: 48, passed: 9 (**pass_fraction 0.1875**)
- by_asset_class: equity 9/24, crypto 0/24
- by_vol_regime: low 8/16, mid 1/16, high 0/16
- best_cell: extreme_pctile=90/lookback_years=5, SPY, low-vol, Sharpe=2.662
- worst_cell: extreme_pctile=90/lookback_years=5, SPY, mid-vol, Sharpe=0.373

## Single-config validation (Step 7) — lookback_days=252, extreme_pctile=90.0, lookback_years=5

| Symbol | Sharpe | MDD | Sharpe pass | MDD pass |
|---|---|---|---|---|
| QQQ | 1.025 | 0.286 | PASS (barely, 1.025≥1.0) | **FAIL** (0.286>0.25) |
| SPY | 0.762 | 0.341 | FAIL | FAIL |

Parameter sweep (QQQ, extreme_pctile ∈ {70,80,85,90} × lookback_years ∈
{3,5}): Sharpe ranges 0.866–1.025, but **max drawdown is IDENTICAL
(0.2856) across every single parameter combination tested** — the
extreme-return gate never actually screens out the drawdown event. Root
cause identified: the max-drawdown episode is the March 2020 COVID crash.
Trailing 12-month momentum going into March 2020 was still comfortably
positive (the prior 12 months, March 2019–Feb 2020, were a strong bull
run) and had NOT yet registered as a return-magnitude "extreme" — the
crash itself is what pushes the trailing-return magnitude into the
extreme percentile, but by the time the (monthly-rebalanced) gate reacts,
the drawdown has already happened. A monthly-rebalanced, trailing-return-
magnitude-based gate is structurally too slow to prevent this specific
class of drawdown (a fast/violent regime break), regardless of how the
percentile threshold is tuned.

## Decision: REJECTED

Genuine near-miss on Sharpe (QQQ passes barely at extreme_pctile=90) but
decisive, parameter-invariant failure on max drawdown (0.286, every
config, both symbols) driven by a single unavoidable crash event the
monthly-rebalanced extreme-return gate cannot react to in time. Crypto
falsification symbols reject decisively (0/24) as expected — trailing
12-month absolute momentum is not the repo's typical crypto signal
construction. Flagged for a future loop: a faster-reacting drawdown
circuit-breaker (e.g. a hard stop-loss or daily-rebalanced realized-vol
kill-switch layered ON TOP of the monthly TSMOM decision, rather than
relying on the monthly-rebalanced return-magnitude percentile alone)
would be the natural next fix attempt, distinct from simply re-tuning
`extreme_pctile`/`lookback_years` (already shown not to move the MDD
needle at all).

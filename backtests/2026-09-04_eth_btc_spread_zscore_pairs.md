# ETH/BTC Log-Spread Z-score Pairs Trade (Long-only ETH leg) — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_eth_btc_spread_zscore_pairs.py`
**Outcome:** REJECTED

## Hypothesis

Per https://validatedstrategies.com/strategy/pairs-eth-btc's own writeup:
ETH/BTC prices are hypothesized to be cointegrated, so the log(ETH/BTC)
spread should mean-revert; z-score the daily spread, enter (long ETH /
short BTC in the source's real pairs trade) when z < -2, exit at z >= 0,
stop-loss at |z| >= 3.5. First cross-asset spread/pairs strategy tested in
this repo. Adapted here as a **long-only ETH leg approximation** (no
shorting BTC — this repo's `generate_returns` contract is single-series),
explicitly NOT market-neutral like the source's real pairs trade — a
known, documented simplification.

Source: https://validatedstrategies.com/strategy/pairs-eth-btc (found via
Google search fallback; `web_search` failed with a DDGS/Yahoo TLS
connection error on this query). Notably, the source itself already
backtested the real (short-BTC) version over 2018-2026 and rejected it
decisively: not cointegrated (Engle-Granger p=0.32/0.65, Johansen trace
below critical values, rolling cointegration only 7.6% of windows),
486-day spread half-life, -93.3% max drawdown from the 2021 ETH re-pricing
regime break, and fails a placebo/permutation test (58% of random
sign-flips beat it).

## Grid test summary (window x entry_z, ETH/USDT only, 3 vol regimes)

- total_cells: 27, passed_cells: 0, **pass_fraction: 0.000**
- by_vol_regime: low 0/9, mid 0/9, high 0/9
- best_cell: window=20/entry_z=2.5, mid-vol regime, Sharpe only 0.214
- worst_cell: window=60/entry_z=2.5, low-vol regime, Sharpe -0.188

## Full-sample Sharpe by config

| config | Sharpe |
|---|---|
| window=30, entry_z=2.0, hold=20 | 0.055 |
| window=20, entry_z=2.0, hold=10 | 0.114 |
| window=60, entry_z=1.5, hold=30 | 0.080 |
| window=30, entry_z=2.5, hold=20 | 0.049 |

## Single-config validators (primary config: window=30, entry_z=2.0,
exit_z=0.0, stop_z=3.5, max_hold_days=20)

| validator | passed | value | threshold |
|---|---|---|---|
| sharpe_ratio | **FAIL** | 0.055 | 1.0 |
| max_drawdown | **FAIL** | 0.784 | 0.25 |
| transaction_cost_survival | **FAIL** | -0.040 (net Sharpe after costs) | 0.5 |

2224 trades (!) over 7.7yr on this config — the long-only single-leg
approximation appears to flip position far more often than a real hedged
pairs trade would need, since without the short-BTC leg to dampen net P&L
noise, small spread wiggles around the entry/exit thresholds trigger
frequent re-entries; net-of-cost Sharpe goes negative.

## Decision

**Rejected, decisively (0/27 grid cells).** Confirms the source's own
finding that the ETH/BTC spread relationship does not persist tradeably
even independent of the specific gate methodology (this repo's Sharpe/MDD/
TC-survival vs. the source's profit-factor/placebo tests both reach the
same negative verdict). The 78% max drawdown on the primary config is the
worst of any strategy tested in this repo to date, consistent with the
source's own -93.3% finding on the real hedged version — the 2021 ETH
re-pricing regime break destroys this trade regardless of hedge structure.
Not implemented as a live strategy. This repo's single-series
`generate_returns` interface is not well-suited to true market-neutral
pairs trades (no short-leg P&L) — a future loop wanting to test pairs
trading properly would need to extend the strategy interface to return a
two-leg net P&L series rather than approximate with a long-only leg.

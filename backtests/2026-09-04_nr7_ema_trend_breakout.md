# NR7 (Narrow Range 7) EMA-Trend Breakout — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_nr7_ema_trend_breakout.py`
**Outcome:** REJECTED

## Hypothesis

Toby Crabel's NR7 pattern (narrowest-range bar of the last 7 bars) is a
range-contraction preceding range-expansion. Per
https://www.tradingsetupsreview.com/nr7-trading-strategy/'s concrete rule
(originally for 3-minute intraday CL futures bars, adapted here to daily
bars): when the trailing N bars are all above a 20-EMA (confirmed uptrend),
a breakout above the NR bar's high is a low-risk long entry that continues
the trend. Distinct from prior breakout strategies in this repo (Donchian
-008/-054, BB-squeeze) because the trigger level is defined by a
volatility-contraction bar, not a rolling channel or fixed-width band.

Source: https://www.tradingsetupsreview.com/nr7-trading-strategy/ (found via
Google search fallback after `web_search` failed with a DDGS/Yahoo TLS
connection error on this query; quantifiedstrategies.com's own NR7 article
appeared in the same search but was not opened, only its snippet).

## Grid test summary (nr_window x ema_window x max_hold_days, 2 equity + 2
crypto symbols, 3 vol regimes)

- total_cells: 144, passed_cells: 17, **pass_fraction: 0.118**
- by_asset_class: equity 17/72, crypto **0/72**
- by_vol_regime: low 16/48, mid 1/48, high 0/48
- best_cell: QQQ, nr_window=5/ema_window=20/max_hold_days=10, low-vol regime,
  Sharpe 2.27
- worst_cell: QQQ, nr_window=7/ema_window=50/max_hold_days=5, high-vol
  regime, Sharpe -2.09

## Full-sample Sharpe by config (equity only)

| config | QQQ | SPY |
|---|---|---|
| nr=5, ema=20, hold=10 | 0.617 | -0.025 |
| nr=7, ema=20, hold=10 | -0.109 | -0.401 |
| nr=5, ema=20, hold=5  | 0.179 | 0.166 |
| nr=10, ema=20, hold=10| -0.105 | -0.417 |

## Single-config validators (primary config: QQQ, nr_window=5,
ema_window=20, max_hold_days=10)

| validator | passed | value | threshold |
|---|---|---|---|
| sharpe_ratio | **FAIL** | 0.617 | 1.0 |
| max_drawdown | pass | 0.136 | 0.25 |
| transaction_cost_survival | **FAIL** | 0.341 (net Sharpe after costs) | 0.5 |

140 round-trip trades over 7.7yr; 10bps/trade cost drag ~0.14 knocks the
already-sub-threshold full-sample Sharpe down further.

## Decision

**Rejected.** Full-sample Sharpe on the best config (QQQ, 0.617) is well
below the 1.0 threshold, and net-of-cost Sharpe (0.341) misses the 0.5
transaction-cost-survival threshold too. The grid's strong low-vol-regime
cells (best 2.27) don't generalize to the full sample or to mid/high-vol
regimes — a classic case of the pattern only firing well in a narrow
subset of conditions, consistent with the source's own explicit caution
that NR7 breakouts near trend extremes or in choppy congestion are
unreliable. Crypto rejected decisively (0/72 grid cells). Not implemented
as a live strategy.

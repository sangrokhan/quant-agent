# ATR-Brick Renko Trend Following + 200-SMA Filter — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_renko_atr_trend_follow.py`
**Outcome:** REJECTED

## Hypothesis

Per Google's AI-overview summary of TheStopHunter/Tradinformed Renko
trend-following guides: reconstructing price into fixed-size "bricks"
(ATR-based brick size here, since this repo has no tick-data source)
strips time-axis noise; a long entry triggers when price is above a
200-SMA trend filter AND N consecutive up-bricks form after a
down-brick sequence. Exit on the first down-brick (color-flip) or a
trend-filter break. First Renko-style strategy tested in this repo.

Source: Google AI-overview + TheStopHunter/Tradinformed search snippets
(found via `browser_exec` after `web_search` failed with a DDGS/Yahoo TLS
connection error on this query).

## Grid test summary (atr_window x trend_window x confirm_bricks, 2
equity + 2 crypto symbols, 3 vol regimes)

- total_cells: 144, passed_cells: 36, **pass_fraction: 0.250**
- by_asset_class: equity 36/72, crypto **0/72**
- by_vol_regime: low 24/48, mid 12/48, high **0/48**
- best_cell: SPY, atr_window=14/trend_window=200/confirm_bricks=1,
  low-vol regime, Sharpe 2.15

## Full-sample Sharpe by config (equity only)

| config | QQQ | SPY |
|---|---|---|
| atr=14, trend=200, confirm=1 | 0.682 | 0.665 |
| atr=14, trend=200, confirm=2 | 0.806 | 0.532 |
| atr=10, trend=200, confirm=1 | 0.733 | 0.638 |
| atr=14, trend=100, confirm=1 | 0.611 | 0.628 |

## Single-config validators (primary config: QQQ, atr_window=14,
trend_window=200, confirm_bricks=2 — best full-sample config found)

| validator | passed | value | threshold |
|---|---|---|---|
| sharpe_ratio | **FAIL** | 0.806 | 1.0 |
| max_drawdown | pass | 0.224 | 0.25 |
| transaction_cost_survival | pass | 0.563 (net Sharpe after costs) | 0.5 |

148 round-trip trades over 7.7yr; MDD and cost-survival both pass
comfortably, but Sharpe falls short across every tested config on both
symbols.

## Decision

**Rejected.** No config on QQQ or SPY reaches the 1.0 Sharpe threshold
on the full sample (best: QQQ 0.806). The strong low-vol-regime grid
cells (best 2.15) concentrate almost entirely in low/mid-vol regimes
(0/48 in high-vol), consistent with a trend-following strategy that
loses its edge when volatility spikes and price whipsaws through the
ATR-brick boundaries in both directions. Crypto rejected decisively
(0/72 grid cells). Not implemented as a live strategy. A future loop
could try tightening the trend filter (e.g. require SMA itself sloping
up, not just price above it) or gating entries out of high-vol regimes
explicitly, similar to the approach in 2026-09-03-001.

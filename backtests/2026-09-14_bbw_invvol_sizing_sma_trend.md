# Bollinger BandWidth Inverse-Volatility Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-150
**File:** `strategies/2026-09-14_bbw_invvol_sizing_sma_trend.py`

## Hypothesis

Bollinger BandWidth (BBW, John Bollinger): `BBW = (Upper-Lower)/Middle*100`
using the standard 20-period/2-std Bollinger Bands — a pure volatility-
compression gauge, distinct from %B (price position within bands). Formula
confirmed via Google AI-overview synthesis of ChartSchool/QuestDB
(`browser_exec`).

This repo has 5+ prior Bollinger-squeeze-family entries, all using BBW as a
BINARY compression-then-breakout GATE. This iteration follows the GAPO
(2026-09-14-137) pattern: min-max normalize BBW, INVERT it (compression
scales exposure UP, expansion scales exposure DOWN), applied within an
SMA(trend_window) uptrend gate. First BBW continuous-sizing / inverse-
volatility-conditioning variant in this repo.

## Grid test summary (Step 6)

`param_grid={bb_window: [15,20,25], deadband: [0.15,0.25], leverage_cap: [0.4,1.0]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 144, **passed:** 71, **pass_fraction:** 0.493
- **by_asset_class:** equity 36/72 (0.5), crypto 35/72 (0.486) — balanced.
- **by_vol_regime:** low 40/48 (0.833), mid 25/48 (0.521), high 6/48
  (0.125) — usual concentration in low/mid-vol regimes.
- **best_cell:** SPY, bb_window=15/deadband=0.25/leverage_cap=1.0, low-vol,
  Sharpe 2.71.
- **worst_cell:** QQQ, bb_window=20/deadband=0.25/leverage_cap=0.4,
  high-vol, Sharpe -0.42.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | bw=15, db=0.15, lc=1.0 | 1.177 (pass) | pass | **FAIL (net Sharpe 0.388)** | pass | pass | **rejected (near-miss on TC)** |
| SPY | bw=20, db=0.25, lc=1.0 | 1.166 (pass) | pass | pass | pass | pass | **accepted** |
| BTC/USDT | bw=20, db=0.15, lc=0.4 | 1.343 (pass) | pass | pass | pass | pass | **accepted** |
| ETH/USDT | bw=25, db=0.25, lc=0.4 | 1.250 (pass) | pass | pass | pass | pass | **accepted** |

## Decision

**Accepted:** SPY, BTC/USDT, ETH/USDT (all 5 validators pass).
**Rejected:** QQQ (near-miss, transaction-cost survival fails, 323 trades /
net Sharpe 0.388; gross Sharpe/MDD/WF/param-sensitivity all pass — an
inverted near-miss pattern vs most of this cron trigger's QQQ-passes/SPY-
fails cases, worth noting since QQQ specifically failed TC-survival here
while SPY passed on the same mechanism).

Full raw grid: `grid_result_bbw_invvol_sizing.json`. Full raw validators:
`validators_bbw_invvol_sizing.json`.

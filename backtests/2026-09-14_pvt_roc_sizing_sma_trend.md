# PVT Rate-of-Change Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-152
**File:** `strategies/2026-09-14_pvt_roc_sizing_sma_trend.py`

## Hypothesis

Price and Volume Trend (PVT): cumulative volume indicator scaling each
bar's volume by that day's PERCENTAGE price change,
`PVT_t = PVT_{t-1} + Volume_t*(Close_t-Close_{t-1})/Close_{t-1}` — distinct
from OBV's simple ±full-volume step.

This repo has 2 prior PVT entries, both binary PVT-vs-own-EMA-signal-line
crossovers. Since raw PVT is cumulative/nonstationary (same issue OBV had),
this iteration applies the identical rate-of-change reframing technique
validated this cron trigger for OBV (2026-09-14-151): PVT's own rolling rate
of change, rolling z-scored + tanh-squashed to [-1,+1], sized within an
SMA(trend_window) uptrend gate. First PVT continuous-sizing variant.

## Grid test summary (Step 6)

`param_grid={roc_window: [10,20,30], deadband: [0.15,0.25], leverage_cap: [0.4,1.0]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 144, **passed:** 87, **pass_fraction:** 0.604 — **best
  pass_fraction of any strategy this cron trigger.**
- **by_asset_class:** equity 42/72 (0.583), crypto 45/72 (0.625).
- **by_vol_regime:** low 47/48 (0.979), mid 28/48 (0.583), high 12/48
  (0.25).
- **best_cell:** QQQ, roc_window=10/deadband=0.25/leverage_cap=1.0, low-vol,
  Sharpe 2.83.
- **worst_cell:** QQQ, roc_window=20/deadband=0.15/leverage_cap=0.4,
  high-vol, Sharpe 0.35 (notably not negative — even the worst grid cell
  stayed positive, unusual for this cron trigger's typical worst cells).

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | rw=10, db=0.15, lc=0.4 | 1.465 (pass) | pass | pass | pass | pass | **accepted** |
| SPY | rw=20, db=0.25, lc=1.0 | 1.368 (pass) | pass | pass | pass | pass | **accepted** |
| BTC/USDT | rw=30, db=0.25, lc=0.4 | 1.456 (pass) | pass | pass | pass | pass | **accepted** |
| ETH/USDT | rw=10, db=0.15, lc=0.4 | 1.352 (pass) | pass | pass | pass | pass | **accepted** |

## Decision

**Accepted (ALL FOUR SYMBOLS):** QQQ, SPY, BTC/USDT, ETH/USDT — all 5
validators pass for every symbol. This is the **full clean sweep** result
of this cron trigger: no near-misses, no rejections, on the best grid
pass_fraction observed this run.

Full raw grid: `grid_result_pvt_roc_sizing.json`. Full raw validators:
`validators_pvt_roc_sizing.json`.

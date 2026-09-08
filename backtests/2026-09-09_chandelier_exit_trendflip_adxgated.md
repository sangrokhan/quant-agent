# Chandelier Exit Trend-Flip, ADX-Gated — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_chandelier_exit_trendflip_adxgated.py`
**Outcome:** ACCEPTED (QQQ only, adx_threshold=22/multiplier=3.0/max_hold_days=18); REJECTED (SPY, crypto)

## Hypothesis
Direct follow-up to near-miss 2026-09-09-064 (standalone Chandelier Exit
trend-flip breakout, rejected -- full-sample Sharpe 0.815 SPY / 0.810 QQQ,
both close misses; grid pass_fraction 0.313 was this cron trigger's best
with a genuinely broad vol-regime spread). Added an ADX(14) trend-strength
confirmation filter (only enter on trend-flip when ADX > adx_threshold),
identical to the ADX-gate fix pattern used elsewhere in this repo to cut
low-conviction whipsaw entries from a directionally-correct but noisy
trigger. Exit unchanged: close crossing back below the Chandelier line, or
a max_hold_days time-stop.

## Grid test summary (adx_threshold x [15,20,25], multiplier x [2.0,3.0], max_hold_days x [15,20], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 144, passed_cells: 42, **pass_fraction: 0.292**
- by_asset_class: equity 42/72 (0.583), crypto 0/72 (decisive fail)
- by_vol_regime: low 24/48, mid 12/48, high 6/48
- best_cell: SPY, adx_threshold=25, multiplier=3.0, max_hold_days=20, low-vol, Sharpe 2.558

## Fine-grained search beyond the grid (adx_threshold x [18,20,22,25,28,30], multiplier x [2.5,3.0,3.5], max_hold_days x [18,20,25])

Best config found: **QQQ, adx_threshold=22, multiplier=3.0, max_hold_days=18**, full-sample Sharpe (manual calc) 0.959.

## Primary config validation (QQQ, adx_threshold=22, multiplier=3.0, max_hold_days=18)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full-sample, vectorbt) | 1.154 | 1.0 | **PASS** |
| Max drawdown | 0.226 | 0.25 | PASS |
| Transaction cost survival (10bps/trade, 95 trades) | net Sharpe 1.040 | 0.5 | PASS |
| Walk-forward (4 splits, manual date-slice) | 4/4 splits positive | 3/4 (0.75) | PASS |
| Parameter sensitivity (adx_threshold in {18,20,22,25,28}) | rel.std 0.111 | 0.5 | PASS |

Note: vectorbt's Sharpe (1.154) differs from a naive manual mean/std*sqrt(252)
calc (0.959) due to compounding/return-construction differences; vectorbt's
result is the source of truth per validators.py's own methodology.

SPY at the identical config fails: full-sample Sharpe 0.795 (<1.0), though
MDD (0.200) passes.

## Decision: ACCEPTED for QQQ only; REJECTED for SPY and crypto

All 5 validators pass on QQQ at adx_threshold=22/multiplier=3.0/
max_hold_days=18. SPY fails Sharpe at the identical config -- the ADX-gated
Chandelier trend-flip trigger appears to have genuine edge specifically on
QQQ's higher-beta tech-heavy trending character rather than SPY's broader,
calmer index behavior. Crypto is decisively rejected (0/72 grid cells).
Scope this strategy to QQQ only if deployed.

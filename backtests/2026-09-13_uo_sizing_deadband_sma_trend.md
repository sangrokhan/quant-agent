# Ultimate Oscillator Continuous Sizing + Exposure-Change Deadband on SMA(200) — Backtest Report

**Date:** 2026-09-13 | **KB id:** 2026-09-13-079 | **Outcome:** ACCEPTED (QQQ, all 5 validators); SPY near-miss (Sharpe 0.760<1.0); crypto decisively rejected

## Hypothesis
Direct fix for 2026-09-13-077 (UO continuous sizing, rejected decisively on TC survival — net
Sharpe went NEGATIVE after costs, ~1800 trades). Reuses the exposure-change deadband technique
that just fixed the analogous CMO-sizing TC failure this same cron trigger (2026-09-13-078).
Widened deadband grid upward (0.10-0.20) given UO's ~3x higher raw turnover vs CMO.

## Grid test (Step 6)
`scripts/run_grid_uo_deadband.py`, param_grid: deadband∈{0.10,0.15,0.20}, uo_sensitivity∈{0.4,0.6},
base_exposure∈{0.8,1.0}; symbols equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3.
2017-01-01 to 2026-09-01.

- total_cells=144, passed=36, **pass_fraction=0.25**
- by_asset_class: equity 36/72; **crypto 0/72 (decisive fail, same as underlying 077)**
- by_vol_regime: low 24/48, mid 12/48, **high 0/48**
- best_cell: QQQ, deadband=0.20, uo_sensitivity=0.6, base_exposure=0.8, low-vol, Sharpe=2.51

## Single-config validation (Step 7) — best config deadband=0.20, uo_sensitivity=0.6, base_exposure=0.8

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>1.0) | **PASS** 1.088 | **FAIL (near-miss)** 0.760 |
| Max Drawdown (<0.25) | PASS 0.196 | PASS 0.182 |
| Transaction cost survival (net Sharpe >0.5 @10bps) | **PASS** 0.986 (87 trades, down from 1826 raw) | **PASS** 0.584 (108 trades, down from 1810 raw) |
| Walk-forward (4-split, ≥0.75 pass) | PASS 1.0 | PASS 0.75 |
| Parameter sensitivity (rel. std <0.5) | PASS 0.011 | PASS 0.029 |

## Decision: ACCEPTED for QQQ (all 5 validators pass); SPY near-miss (Sharpe fail only); crypto decisively rejected.

A wider deadband (0.20 vs CMO's 0.10) was needed to tame UO's higher raw turnover, but the fix
worked just as decisively: trades fell ~21x (1826→87 QQQ, 1810→108 SPY) and net-of-cost Sharpe
flipped from strongly negative (-0.124/-0.252) to comfortably passing (0.986/0.584), while raw
directional Sharpe stayed essentially unchanged (1.088 vs 1.105 QQQ) and parameter sensitivity
tightened. This is the second consecutive confirmation this cron trigger (after CMO 078) that
un-smoothed multi-window-sum oscillators are viable continuous-sizing dials once an
exposure-change deadband controls turnover — the earlier TC rejections (076, 077) were purely
a turnover problem, not a signal-quality problem.

## Note for future iterations
Two-for-two on the "deadband fixes TC-rejected sizing overlay" pattern (CMO, UO). If another
sizing-overlay TC rejection occurs, try this fix before abandoning the underlying indicator.
QQQ-accepted-only / SPY-near-miss / crypto-decisively-rejected is now the dominant recurring
outcome pattern for the SMA(200)-gated continuous-sizing family in this repo (6 of the last 7
accepted-or-near-accepted entries this cron trigger share this exact scope).

# Kase Peak Oscillator (KPO) Zero-Line Crossover — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_kase_peak_oscillator_zerocross.py`
**Outcome:** REJECTED

## Hypothesis
Cynthia Kase's Peak Oscillator (via Mladen's MQL4 port on the ProRealCode forum,
https://www.prorealcode.com/topic/kase-peak-oscillator-kase-cd-and-kase-permission/)
measures the ratio of the maximum recent directional move (over a short..long
cycle band) to a volatility normalizer, differencing the "up" leg from the "down"
leg. Long entry on KPO crossing above zero, exit on cross below zero or a
max_hold_days time-stop. First Kase Peak Oscillator strategy in this repo.

## Grid test summary (sensitivity x [30,40,55], max_hold_days x [10,15,20], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 108, passed_cells: 24, **pass_fraction: 0.222**
- by_asset_class: equity 24/54 (0.444), crypto 0/54 (0.0, decisive fail)
- by_vol_regime: low 12/36, mid 9/36, high 3/36 (concentrated in low/mid vol)
- best_cell: SPY, sensitivity=30, max_hold_days=20, low-vol regime, Sharpe 2.003
- worst_cell: BTC/USDT, sensitivity=30, max_hold_days=10, low-vol regime, Sharpe -0.030

## Primary config validation (SPY, sensitivity=30.0, max_hold_days=20 — best avg full-sample config)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full-sample) | 0.992 | 1.0 | **FAIL** (near-miss, 0.008 short) |
| Max drawdown | 0.136 | 0.25 | PASS |

QQQ full-sample Sharpe at the same config: 0.727 (also fails, wider margin).

Given the full-sample Sharpe decisively fails on QQQ (0.727) and is a
near-miss fail on SPY (0.992 vs 1.0 threshold), and crypto is a decisive 0/54
across the entire grid, the primary-config validator suite fails at the first
gate (Sharpe). No further validators (walk-forward, TC-survival,
parameter-sensitivity) were run since Step 8's accept bar requires all
validators to pass and Sharpe already fails.

## Decision: REJECTED

Full-sample Sharpe fails on both equity symbols at their best grid config
(QQQ 0.727 decisive, SPY 0.992 near-miss); grid pass_fraction 0.222 is
concentrated in low/mid-vol equity cells only; crypto decisively rejected
0/54. SPY's near-miss (0.992) and strong risk profile (MDD 13.6%, best grid
cell Sharpe 2.003) make this a candidate for a future revisit with a
regime/volatility gate or a stricter peak-band entry (the source's own
higher-conviction "peak" signal, distinct from the simple zero-cross tested
here) rather than the plain zero-line crossover.

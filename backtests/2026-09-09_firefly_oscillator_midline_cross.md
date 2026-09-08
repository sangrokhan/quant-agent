# Firefly Oscillator Midline Crossover — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_firefly_oscillator_midline_cross.py`
**Outcome:** ACCEPTED (SPY only, basis_length=14/max_hold_days=10); REJECTED (QQQ, crypto)

## Hypothesis
LuxAlgo's Firefly Oscillator (https://www.luxalgo.com/library/indicator/firefly-oscillator/)
converts a weighted price ((H+L+2C)/4) into a z-score against its own rolling
EMA basis and stdev, double-smooths that z-score with a zero-lag EMA pass,
and rescales to a 0-100 range where 50 is neutral. Per source's own trading
guide, a cross of the midline (50) is the primary directional signal. Long
entry on midline cross-up, exit on cross-down or a max_hold_days time-stop.
First Firefly Oscillator strategy in this repo.

## Grid test summary (basis_length x [8,10,14], max_hold_days x [10,15,20], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 108, passed_cells: 27, **pass_fraction: 0.250**
- by_asset_class: equity 27/54 (0.5), crypto 0/54 (0.0, decisive fail)
- by_vol_regime: low 17/36, mid 9/36, high 1/36
- best_cell: SPY, basis_length=14, max_hold_days=10, low-vol regime, Sharpe 2.587

## Primary config validation (SPY, basis_length=14, max_hold_days=10)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full-sample) | 1.080 | 1.0 | **PASS** |
| Max drawdown | 0.109 | 0.25 | PASS |
| Transaction cost survival (10bps/trade, 113 trades) | net Sharpe 0.804 | 0.5 | PASS |
| Walk-forward (4 splits, manual date-slice) | 4/4 splits positive | 3/4 (0.75) | PASS |
| Parameter sensitivity (basis_length in {10,12,14,16,18}) | rel.std 0.103 | 0.5 | PASS |

QQQ at the same config fails decisively: full-sample Sharpe 0.713 (<1.0), MDD 0.255 (>0.25).

## Decision: ACCEPTED for SPY only; REJECTED for QQQ and crypto

All 5 validators pass on SPY at basis_length=14/max_hold_days=10. QQQ fails
both Sharpe and MDD at the same config -- the midline-cross entry appears to
work specifically on SPY's lower-volatility, more mean-reverting daily
character rather than QQQ's higher-beta tech-heavy moves. Crypto is
decisively rejected (0/54 grid cells). Scope this strategy to SPY only if
deployed; do not generalize to QQQ or crypto without further tuning.

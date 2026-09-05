# Ehlers Even Better Sinewave (EBSW) Zero-Line Crossover — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_ehlers_ebsw_zerocross.py`
**Source:** https://www.luxalgo.com/library/indicator/even-better-sinewave/

## Hypothesis

Ehlers' Even Better Sinewave high-pass filters price (40-bar duration
default) to drop trend content, SuperSmoothers the result (10-bar critical
period), then normalizes a 3-bar average by the square root of its own
recent power, confining the output to roughly -1..+1. Zero crosses are
"the swing-timing events while the market is cycling." Long entry on EBSW
crossing above zero; exit on the opposite cross or a max_hold_days
time-stop.

## Grid-test summary (Step 6)

Grid: `duration in {30,40,50}`, `max_hold_days in {10,15}`, symbols
`{QQQ, SPY}` (equity) x `{BTC/USDT, ETH/USDT}` (crypto), 3 vol-regime
terciles, 2018-01-01..2026-09-01.

- **Overall pass fraction:** 8/72 = 11.1%
- **By asset class:** equity 8/36 (22.2%); crypto 0/36 (0%) — decisive
  crypto rejection.
- **By vol regime:** low 0/24 (0%), mid 6/24 (25%), high 2/24 (8.3%) —
  edge (what little exists) concentrates in mid-vol regime specifically,
  an unusual pattern (most trend/cycle strategies in this repo favor
  low-vol); may reflect the cycle-detection design needing enough
  volatility to have a clean cyclical structure, but not so much that
  high-frequency noise dominates.
- **Best cell:** QQQ, mid-vol, duration=30/max_hold_days=10, Sharpe 1.64
  (single tercile, not full-sample representative).
- **Worst cell:** SPY, mid-vol, duration=40/max_hold_days=15, Sharpe -0.26.

## Single-config validator results (best grid cell config, full sample)

`duration=30, max_hold_days=10`

### QQQ (2018-01-01 .. 2026-09-01)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 0.685 | >= 1.0 | ❌ |
| Max drawdown | 24.6% | <= 25% | ✅ (barely) |
| TC survival (10bps/trade, 104 trades) | net Sharpe 0.547 | >= 0.5 | ✅ |
| Walk-forward (4 splits) | 3/4 positive (75%) | >= 75% | ✅ |
| Parameter sensitivity | relative std 0.26 | <= 0.5 | ✅ |

### SPY (2018-01-01 .. 2026-09-01), same config

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 0.447 | >= 1.0 | ❌ |
| Max drawdown | 16.3% | <= 25% | ✅ |
| TC survival (10bps/trade, 113 trades) | net Sharpe 0.260 | >= 0.5 | ❌ |
| Walk-forward (4 splits) | 3/4 positive (75%) | >= 75% | ✅ |
| Parameter sensitivity | relative std 0.18 | <= 0.5 | ✅ |

## Decision

**Reject.** Both symbols fail the Sharpe ratio threshold decisively (0.685
QQQ, 0.447 SPY, both well under 1.0); SPY additionally fails
TC-survival due to high trade frequency (113 trades over the sample).
Crypto rejected decisively (0/36 grid cells). The single-line EBSW
construction (no dominant-cycle-period adaptivity, unlike the already-
accepted MAMA/FAMA and rejected classic MESA Sine Wave) produces too many
whipsaw zero-crossings to clear this repo's Sharpe/cost bars.

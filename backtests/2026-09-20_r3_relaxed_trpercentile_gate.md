# Larry Connors R3 (relaxed decline-count) + 20d TR-Percentile Volatility Gate — Backtest Report

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_r3_relaxed_trpercentile_gate.py`
**Source:** https://statoasis.com/overfit/research/larry-connors-r3-strategy-for-index-futuresrebuilt-for-index-futures-(with-a-smarter-filter) (Ali Casey, StatOasis)

## Hypothesis

The classic Connors R3 rule (close>SMA200, RSI(2)<10, RSI(2) declined 3
consecutive days, exit RSI(2)>70) is too strict (few trades). Source's own
fix: relax the decline condition to "at least X of last Y RSI readings
declining" and add a proprietary volatility-contraction filter, which the
source states is best implemented as a 20-day true-range PERCENTILE gate
(low TR percentile = range contraction before reversal). Prior R3 variants
in this repo (2026-09-06-159, 2026-09-07-021, 2026-09-08-087) all use the
strict 3-consecutive-day decline with SMA/fixed-RSI exits; none test a
volatility-percentile entry gate.

## Grid test summary (Step 6)

288 cells: `entry_rsi_level∈{10,15,20} × min_declines∈{2,3} ×
vol_percentile_threshold∈{30,50} × max_hold_days∈{7,10}` on equity
{QQQ,SPY} and crypto {BTC/USDT,ETH/USDT}, 3 vol-regime terciles,
2019-01-01 to 2026-09-01.

- **pass_fraction: 0.122** (35/288)
- **by_asset_class:** equity 26/144, crypto **9/144 (nonzero — notable, first R3 variant with any crypto pass)**
- **by_vol_regime:** low 9/96, mid 15/96, high 11/96 — pass rate spread more evenly across regimes than most prior rejected constructions
- **best_cell:** entry_rsi_level=10, min_declines=2, vol_percentile_threshold=50, max_hold_days=10, SPY, mid-vol regime, Sharpe 2.06

## Single-config validation (Step 7) — best_cell params, full sample 2019-2026

| Validator | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** 0.768 | **FAIL** 0.417 | ≥1.0 |
| Max drawdown | pass 2.5% | pass 5.8% | ≤25% |
| Transaction cost survival | pass 0.727 (9 trades) | **FAIL** 0.386 (13 trades) | ≥0.5 |
| Walk-forward (4 splits) | pass 1.0 (4/4) | pass 1.0 (4/4) | ≥0.75 |
| Parameter sensitivity (entry_rsi 10/15/20) | pass 0.068 | pass 0.344 | ≤0.5 |

## Interpretation

The grid's best_cell Sharpe of 2.06 was a mid-vol-regime-tercile figure on
a very small trade count. Full-sample SPY has only 9 total trades over
~10.5 years and QQQ 13 — too sparse for the mid-vol-slice Sharpe to
generalize; full-sample Sharpe drops to 0.77 (SPY) / 0.42 (QQQ), both below
threshold. Walk-forward passing 4/4 is only weakly informative given so few
trades per split. The relaxed decline-count + TR-percentile gate did
produce this repo's first-ever nonzero crypto pass rate for an R3-family
construction (9/144 cells), a mildly interesting but not currently
actionable finding.

## Decision: **REJECTED**

Full-sample Sharpe fails on both SPY (0.768) and QQQ (0.417); QQQ also
fails transaction-cost survival. Trade count too low for the grid's
mid-vol best-cell Sharpe to be trustworthy.

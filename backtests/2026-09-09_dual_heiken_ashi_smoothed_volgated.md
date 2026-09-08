# Dual Heiken Ashi Smoothed, Volatility-Regime Gated — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_dual_heiken_ashi_smoothed_volgated.py`
**Outcome:** REJECTED

## Hypothesis
Direct follow-up to near-miss 2026-09-09-062 (plain Dual Heiken Ashi
Smoothed, rejected -- full-sample Sharpe failed but grid edge was
concentrated in the low-vol tercile: low 24/48 vs mid 8/48 vs high 0/48).
Added an explicit realized-vol regime gate (20d vol <= trailing 252d
median) restricting entries to low-vol conditions, identical construction
to the accepted 2026-09-03_bb_meanrev_qqq_volregime.py. Thesis: filtering
out the decisive high-vol failure zone should recover a full-sample Sharpe
above 1.0.

## Grid test summary (fast_period x [4,6,10], slow_period x [30,50], max_hold_days x [15,20], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 144, passed_cells: 24, **pass_fraction: 0.167** (WORSE than the ungated version's 0.222)
- by_asset_class: equity 24/72, crypto 0/72
- by_vol_regime: low 24/48, mid 0/48, high 0/48
- best_cell: QQQ, fast_period=10, slow_period=30, max_hold_days=15, low-vol regime, Sharpe 2.149

## Full-sample checks

| Symbol | fast_period | slow_period | max_hold_days | Full-sample Sharpe | Trades |
|---|---|---|---|---|---|
| QQQ | 10 | 30 | 15 | 0.519 | 69 |
| QQQ | 6 | 50 | 15 | 0.349 | 95 |
| QQQ | 10 | 50 | 20 | 0.532 | 69 |
| QQQ | 4 | 30 | 15 | 0.257 | 110 |
| SPY | 10 | 30 | 15 | 0.299 | 73 |
| SPY | 6 | 50 | 15 | 0.339 | 89 |
| SPY | 10 | 50 | 20 | 0.259 | 75 |
| SPY | 4 | 30 | 15 | 0.373 | 103 |

All full-sample Sharpe values are WORSE than the ungated 2026-09-09-062
version (which reached up to 0.834 on QQQ). The vol gate reduces trade
count without improving per-trade edge -- likely because the fast/slow
color-flip system already implicitly requires some directional persistence,
and adding the extra regime filter cuts genuinely profitable trades from
mid-vol periods (which the grid showed had a nonzero pass rate, 8/48, in
the ungated version) along with the unprofitable high-vol ones.

## Decision: REJECTED

The volatility-regime-gate fix pattern that worked for other strategies in
this repo does NOT help here -- it makes full-sample performance worse, not
better. This particular indicator's edge (what little there was) is not
cleanly separable by a simple realized-vol regime split. Abandon this
angle; do not attempt further vol-gate variants of Dual Heiken Ashi
Smoothed.

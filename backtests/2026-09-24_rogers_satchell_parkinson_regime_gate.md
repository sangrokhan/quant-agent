# Rogers-Satchell / Parkinson Volatility-Ratio Trend-vs-Chop Regime Gate

**Strategy file:** `strategies/2026-09-24_rogers_satchell_parkinson_regime_gate.py`
**Date:** 2026-09-24
**Source:** https://www.luxalgo.com/library/concept/rogers-satchell-estimator/

## Hypothesis

Rogers-Satchell (RS) is drift-independent; Parkinson (PK) assumes zero
drift. Per the source, "the spread between Rogers-Satchell and Parkinson
... decomposes measured volatility into wiggle versus one-way drift, a
regime read in itself" -- a low RS/PK ratio should indicate a
trend-dominated regime. This strategy gates a classic SMA fast/slow
crossover trend-following signal by this ratio: only trade the crossover
when RS/PK <= regime_threshold (trend-dominated), staying flat during
high-ratio (chop-dominated) regimes. First Rogers-Satchell strategy in
this repo (0 prior KB hits).

## Grid test (Step 6)

`param_grid`: `regime_threshold` in {0.5,0.6,0.7}, `fast_window` in
{10,20,30}, `slow_window` in {50,75,100}; symbols equity {QQQ, SPY},
crypto {BTC/USDT, ETH/USDT}; `vol_regime_splits=3`. 324 cells total.

- **pass_fraction: 0.0** (0/324) -- decisive, categorical failure across every cell.
- **by_asset_class:** equity 0/162, crypto 0/162.
- **by_vol_regime:** low 0/108, mid 0/108, high 0/108.
- **best cell:** equity/QQQ, regime_threshold=0.7, fast_window=10,
  slow_window=50, high-vol regime, Sharpe 0.92 -- still below the 1.0
  Sharpe threshold used by the grid's own pass/fail criterion.

## Decision (Step 8)

**Rejected — decisively, 0/324 grid cells pass.** The RS/Parkinson ratio
regime-read insight from the source does not translate into a workable
gate for this simple SMA-crossover trend signal at any tested threshold or
SMA-window combination, on either asset class or in any volatility
regime. Not pursued to full single-config validators given the
categorical 0% grid pass rate (no config worth promoting).

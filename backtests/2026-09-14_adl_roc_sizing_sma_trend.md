# Accumulation/Distribution Line (ADL) Rate-of-Change Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-153
**File:** `strategies/2026-09-14_adl_roc_sizing_sma_trend.py`

## Hypothesis

Accumulation/Distribution Line (A/D Line, Marc Chaikin): cumulative
volume-flow, `MFM_t=((Close-Low)-(High-Close))/(High-Low)`,
`ADL_t=ADL_{t-1}+MFM_t*Volume_t`. Distinct from the already-tested Chaikin
Oscillator (EMA(3,ADL)-EMA(10,ADL), 2026-09-14-122) which sizes on the
short-vs-long EMA SPREAD of ADL. This iteration uses the RAW ADL line's own
rolling rate of change instead — the same reframing technique validated
this cron trigger for OBV (2026-09-14-151) and PVT (2026-09-14-152) —
rolling z-scored + tanh-squashed to [-1,+1], sized within an
SMA(trend_window) uptrend gate. First raw-ADL (not Chaikin-Oscillator-
derived) continuous-sizing variant in this repo.

## Grid test summary (Step 6)

`param_grid={roc_window: [10,20,30], deadband: [0.15,0.25], leverage_cap: [0.4,1.0]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 144, **passed:** 81, **pass_fraction:** 0.5625
- **by_asset_class:** equity 35/72 (0.486), crypto 46/72 (0.639).
- **by_vol_regime:** low 48/48 (1.0, ALL low-vol cells pass), mid 29/48
  (0.604), high 4/48 (0.083, weakest high-vol showing of the three
  rate-of-change-based volume strategies this trigger).
- **best_cell:** QQQ, roc_window=30/deadband=0.25/leverage_cap=0.4,
  low-vol, Sharpe 3.13 — highest single-cell Sharpe of this cron trigger.
- **worst_cell:** QQQ, roc_window=20/deadband=0.15/leverage_cap=1.0,
  high-vol, Sharpe -0.66.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | rw=30, db=0.25, lc=0.4 | 1.340 (pass) | pass | pass | pass | pass | **accepted** |
| SPY | rw=10, db=0.15, lc=0.4 | 1.085 (pass) | pass | **FAIL** | pass | pass | **rejected (near-miss on TC)** |
| BTC/USDT | rw=30, db=0.25, lc=0.4 | 1.435 (pass) | pass | pass | pass | pass | **accepted** |
| ETH/USDT | rw=10, db=0.15, lc=0.4 | 1.306 (pass) | pass | pass | pass | pass | **accepted** |

## Decision

**Accepted:** QQQ, BTC/USDT, ETH/USDT (all 5 validators pass at
leverage_cap=0.4).
**Rejected:** SPY (near-miss, transaction-cost survival fails; gross
Sharpe/MDD/WF/param-sensitivity all pass — the same recurring SPY-TC-
survival-near-miss pattern that appears repeatedly across the rate-of-
change-based volume family this cron trigger, e.g. OBV-151, TSV-149).

**Cron-trigger-wide observation:** all three rate-of-change reframings of
cumulative volume indicators this run (OBV-151, PVT-152, ADL-153) show the
same signature: QQQ/BTC/ETH pass decisively while SPY specifically
struggles on transaction-cost survival (except PVT-152, which passed SPY
too, the only full 4-symbol clean sweep of this trigger). Worth a future
iteration specifically retuning SPY's deadband/roc_window for this family.

Full raw grid: `grid_result_adl_roc_sizing.json`. Full raw validators:
`validators_adl_roc_sizing.json`.

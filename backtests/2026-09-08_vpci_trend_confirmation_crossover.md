# VPCI Trend-Confirmation Crossover — Backtest Report

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_vpci_trend_confirmation_crossover.py`
**Knowledge base id:** 2026-09-08-030
**Outcome:** REJECTED

## Hypothesis

Per LazyBear's Volume Price Confirmation Indicator (VPCI, TradingView 2015,
formula per https://pineify.app/pine-script/indicators/vpci):
`VPC = VWMA(close,long_term) - SMA(close,long_term)`;
`VPR = VWMA(close,short_term) / SMA(close,short_term)`;
`VM = SMA(volume,short_term) / SMA(volume,long_term)`;
`VPCI = VPC * VPR * VM`. Long on smoothed-VPCI crossing above zero, exit on
cross below zero or a `max_hold_days` time-stop.

## Grid test summary (96 cells: short_term∈{5,8} × long_term∈{20,30} ×
max_hold_days∈{15,20} × 2 equity symbols × 2 crypto symbols × 3 vol regimes)

- `pass_fraction`: 2.1% (2/96) — decisive fail
- `by_asset_class`: equity 2/48; **crypto 0/48 (decisive reject)**
- `by_vol_regime`: low 2/32; **mid 0/32, high 0/32 (decisive reject)**
- `best_cell`: short_term=5, long_term=30, max_hold_days=20 — equity/SPY/low-vol, Sharpe 1.029

## Single-config confirmation (SPY, full sample 2015-01-01 to 2026-09-01, best grid config)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ FAIL | 0.279 | ≥ 1.0 |
| Max drawdown | ✅ pass (moot) | 15.2% | ≤ 25% |

The single passing grid cell (low-vol tercile) was not representative of
the strategy's full-sample behavior — full-sample Sharpe collapses to
0.279. **REJECT.**

## Analysis

VPCI's triple-multiplicative construction (price-confirmation term ×
short/long ratio term × volume-ratio term) produces a mostly muted,
low-conviction daily signal — the zero-line crossover fires rarely and
without sufficient edge once measured across the full sample. Not pursued
further with a divergence or threshold variant this iteration given the
decisive full-asset-class and full-vol-regime failure.

## Sources

- https://pineify.app/pine-script/indicators/vpci (full disclosed formula
  + default parameters)

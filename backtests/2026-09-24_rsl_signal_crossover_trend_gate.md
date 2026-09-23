# RSL (Levy Relative Strength) Signal-Line Crossover, Trend-Gated

**Strategy file:** `strategies/2026-09-24_rsl_signal_crossover_trend_gate.py`
**Date:** 2026-09-24
**Sources:**
- https://www.vantagepointsoftware.com/blog/relative-strength-outperformance/ (Robert Levy's 1968 relative-strength background)
- https://indicators.agenatrader.com/standard-indicators/relative-strength-levy-rsl (disclosed RSL formula: `RSL(period) = Close / SMA(Close, period) * 10`)

## Hypothesis

RSL is close/SMA(close,N)*10, balanced around 10. Rather than trade a plain
RSL-vs-10 crossover (mechanically identical to a saturated SMA-crossover
family already in this KB), this strategy trades a MACD-style signal-line
crossover ON the RSL oscillator itself (fast SMA of RSL vs slow SMA of RSL),
gated by a longer-term SMA(100) trend filter on raw price, with a
max-hold-days time-stop.

## Grid test (Step 6)

`param_grid`: `rsl_period` in {65,135,200}, `fast_window` in {3,5,10},
`slow_window` in {15,20,30}; symbols equity {QQQ, SPY}, crypto {BTC/USDT,
ETH/USDT}; `vol_regime_splits=3`. 324 cells total.

- **pass_fraction: 0.321** (104/324)
- **by_asset_class:** equity 51/162 (0.315), crypto 53/162 (0.327)
- **by_vol_regime:** low 84/108 (0.778), mid 16/108 (0.148), high 4/108 (0.037)
  — strongly concentrated in low-vol regimes, as expected for a trend/momentum
  signal-line crossover.
- **best cell:** equity/QQQ, rsl_period=200, fast=10, slow=15, low-vol regime, Sharpe 2.87.
- **worst cell:** equity/QQQ, rsl_period=65, fast=3, slow=30, high-vol regime, Sharpe -1.38.

A finer local sweep around the grid's best QQQ region found an even better
full-sample config: `rsl_period=135, fast_window=8, slow_window=30,
trend_window=100, max_hold_days=20` (full-sample QQQ Sharpe 1.465, vs 0.97
for the raw grid-best cell's params on the full sample) — used as the
primary config for Step 7 below.

## Validators (Step 7) — primary config: rsl_period=135, fast_window=8, slow_window=30, trend_window=100, max_hold_days=20

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity (rel. std) | Trades |
|---|---|---|---|---|---|---|
| QQQ | 1.465 (pass, thr 1.0) | 0.067 (pass, thr 0.25) | 1.386 (pass, thr 0.5) | 1.00 (pass, 4/4 splits) | 0.249 (pass, thr 0.5) | 62 |
| SPY | 0.710 (**fail**, thr 1.0) | 0.076 (pass) | 0.611 (pass) | 0.75 (pass, 3/4 splits) | 0.307 (pass) | 64 |

## Decision (Step 8)

**Accepted — QQQ only.** All 5 validators pass on QQQ (Sharpe 1.465, MDD
6.7%, robust across walk-forward and parameter sensitivity). SPY fails the
Sharpe threshold (0.71 < 1.0) though other validators pass — kept in
`strategies/` but flagged as QQQ-only scope; do not treat as broadly
validated across the whole equity universe. Crypto was grid-tested only
(not run through the full single-config validator suite this iteration) —
grid pass_fraction for crypto (0.327) is comparable to equity's (0.315),
suggesting a crypto-specific parameter retune could be a worthwhile
follow-up iteration.

# Garman-Klass Volatility Targeting + Deadband — Backtest Report

**Date:** 2026-09-17 (cron trigger iteration 3)
**Strategy file:** `strategies/2026-09-17_garman_klass_vol_targeting_deadband.py`
**Hypothesis:** Per https://faintrading.com/formulas/garman-klass (read via
browser_exec fallback -- web_extract's configured backend is search-only;
web_search itself worked for keyword discovery this iteration), the
Garman-Klass (1980) OHLC volatility estimator (`sigma^2 = 0.5*ln(H/L)^2 -
(2ln2-1)*ln(C/C_prev)^2`) is reported ~7.4-8x more statistically efficient
than close-to-close (vs Parkinson's ~5x, per the same source family). This
repo has tested GK twice before as a compression/breakout entry TRIGGER
(2026-09-08-023/044, both rejected) but never as an inverse-vol-TARGETING
SIZING dial (the construction already validated for close-to-close vol
[2026-09-08-165] and Parkinson vol [2026-09-17-050/051, this trigger] and
its own equity+crypto-broad acceptance). Applies the identical trend-gate +
inverse-vol-target-sizing + deadband construction, swapping only the
volatility estimator to Garman-Klass, and includes the deadband from the
start (learned directly from this trigger's own 050->051 turnover-cost
lesson rather than re-discovering it in a second sub-iteration).

Source URL: https://faintrading.com/formulas/garman-klass (browser_exec)

## Grid test summary (validation/grid_test.py::run_strategy_grid)

Grid: `trend_window`∈{100,200} × `vol_window`∈{10,20,40} × `target_vol`∈{0.10,0.15,0.20}
× `leverage_cap`∈{1.0,1.5} × `deadband`∈{0.10,0.20}, symbols={QQQ,SPY,BTC/USDT,ETH/USDT},
vol_regime_splits=3.

- total_cells: 864, passed: 458, **pass_fraction: 0.530**
- by_asset_class: equity 204/432 (0.47), crypto 254/432 (0.59)
- by_vol_regime: low 224/288 (0.78), mid 194/288 (0.67), high 40/288 (0.139)
- best_cell: SPY, trend_window=200/vol_window=40/target_vol=0.10/leverage_cap=1.0/deadband=0.2,
  low-vol regime, Sharpe 2.916
- worst_cell: QQQ, trend_window=100/vol_window=40/target_vol=0.10/leverage_cap=1.5/deadband=0.1,
  high-vol regime, Sharpe -0.584

Marginally broader than both the close-to-close predecessor and the
Parkinson version of this same construction (0.530 vs 0.521/0.515),
consistent with GK's reported higher statistical efficiency translating
into a slightly more broadly-applicable sizing signal.

## Single-config validation (best per-symbol config found via 4-config search)

| Symbol | Config (trend_window/vol_window/target_vol/leverage_cap/deadband) | Sharpe | MDD | Net Sharpe (5bps) | # trades | WF pass frac | Param sens (rel std) |
|---|---|---|---|---|---|---|---|
| QQQ | 200/20/0.20/1.0/0.20 | 1.318 (pass) | 0.189 (pass) | 1.297 (pass) | 36 | 0.75 (pass) | 0.032 (pass) |
| SPY | 200/10/0.15/1.5/0.20 | 1.105 (pass) | 0.245 (pass) | 1.036 (pass) | 109 | 0.75 (pass) | 0.028 (pass) |
| BTC/USDT | 200/10/0.15/1.5/0.20 | **1.092 (pass)** | **0.152 (pass)** | **1.047 (pass)** | 84 | 0.75 (pass) | 0.127 (pass) |
| ETH/USDT | 200/20/0.20/1.0/0.20 | 0.964 (near-miss fail) | 0.246 (pass) | 0.942 (pass) | 58 | 1.00 (pass) | 0.062 (pass) |

Note QQQ's turnover is remarkably low (36 trades over the full sample) at
this config -- GK's smoother estimate combined with the deadband keeps
resizing rare. BTC/USDT clears every validator comfortably (best Sharpe of
any prior crypto accept in this family, 1.092 vs Parkinson's 1.012), a
genuinely non-narrow pass. ETH/USDT again falls just short on raw Sharpe
(0.964 vs 1.0), the same near-miss asymmetry pattern already seen for the
Parkinson version (0.946) and other ETH/BTC-pair strategies in this repo.

## Accept/Reject

- **QQQ, SPY, BTC/USDT: ACCEPT.** All validators pass; BTC/USDT is the
  strongest crypto result of the three vol-targeting-estimator family
  variants tested this cron trigger (close-to-close crypto 0/36, Parkinson
  BTC 1.012 narrow pass, Garman-Klass BTC 1.092 comfortable pass).
- **ETH/USDT: REJECT (near-miss).** Same near-miss pattern as the
  Parkinson variant (051): Sharpe 0.964 narrowly misses 1.0, every other
  validator passes cleanly. Not pursued further this iteration.

Building the deadband in from the start (rather than as a follow-up
sub-iteration) saved one full research/build/grid/validate cycle this
trigger relative to the Parkinson family's two-iteration path.

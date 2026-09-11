# Ehlers Adaptive SuperSmoother Crossover — Backtest Report

**Date:** 2026-09-12
**Strategy file:** `strategies/2026-09-12_ehlers_adaptive_supersmoother_crossover.py`
**Source:** TASC September 2026 Traders' Tips (John F. Ehlers, "Improved Filter
Performance"), via https://www.tradingview.com/scripts/tasc/

## Hypothesis

Compute a fixed-period (20) 2-pole SuperSmoother on close; derive an adaptive
period from the fixed filter's own ROC/RMS (scaled, clipped, squared);
compute a second SuperSmoother using that adaptive period. Long when the
Adaptive SuperSmoother > fixed-period SuperSmoother, flat otherwise, with a
min_hold_days hysteresis gate to reduce whipsaw.

## Best config (from grid search)

`base_period=30, min_hold_days=5` (rms_length=81 default, max_hold_days=60 default)

## Single-config validator results (2018-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass | Param sensitivity (rel. std) |
|---|---|---|---|---|---|
| QQQ | 1.378 (pass, thr 1.0) | **26.9% (FAIL, thr 25%, near-miss)** | 1.335 (pass, thr 0.5) | 4/4 (pass) | 0.192 (pass, thr 0.5) |
| SPY | **0.965 (FAIL, thr 1.0, near-miss)** | **28.7% (FAIL, thr 25%)** | 0.914 (pass, thr 0.5) | 4/4 (pass) | 0.091 (pass, thr 0.5) |

Both symbols fail at least one validator at full-sample.

## Grid-test summary (2019-01-01 to 2026-09-01)

Grid: `base_period in {15, 20, 30} x min_hold_days in {3, 5, 10}`, symbols
`{QQQ, SPY} x {BTC/USDT, ETH/USDT}`, vol_regime_splits=3. 108 total cells.

- Overall pass_fraction: 0.25 (27/108)
- By asset class: equity 27/54 passed; **crypto 0/54 passed (decisive reject)**
- By vol regime: low 18/36, mid 6/36, high 3/36
- Best cell: QQQ, base_period=30/min_hold_days=5, low-vol, Sharpe 2.15
- Worst cell: BTC/USDT, base_period=15/min_hold_days=3, mid-vol, Sharpe 0.033

## Decision: REJECT (both equity symbols fail full-sample; crypto decisively rejected)

QQQ fails max-drawdown by a narrow margin (26.9% vs 25% threshold) despite
strong Sharpe/TC/walk-forward/param-sensitivity. SPY fails both Sharpe
(0.965, a near-miss) and max-drawdown (28.7%). The strategy holds up well
in the grid's low-vol tercile (18/36 there) but degrades sharply in mid/high
vol, consistent with the full-sample MDD failures. A future iteration could
retry with an explicit vol-regime gate (flat during high realized-vol, as
several prior accepted strategies in this repo do) as a fix, but that is not
attempted this iteration.

# Keltner Channel Middle-Line Pullback + Min-Hold-Days Gate — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_keltner_midline_pullback_minhold.py`
**Direct follow-up to:** 2026-09-06-136 (near-miss, rejected for TC-survival)

## Hypothesis

2026-09-06-136 (Keltner Channel middle-line pullback trend-continuation)
had a near-miss raw Sharpe (0.965 SPY) and clean parameter sensitivity
(0.309), but was decisively rejected on transaction-cost-survival: 442
trades over 7.7yr let 10bps/trade costs flip net Sharpe negative (-0.089).
This iteration applies the same `min_hold_days` fix pattern already
validated 3x in this repo (Klinger 2026-09-04-085, ZLEMA 2026-09-06-171,
Accelerator Oscillator 2026-09-06-174): suppress all exit checks for the
first N days after entry to cut trade count, leaving entry/exit signal
logic otherwise identical.

## Grid test (Step 6)

`param_grid={"min_hold_days": [5,10,15], "trend_window": [50,100]}`,
symbols QQQ/SPY/BTC-USDT/ETH-USDT, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01.

- **72 total cells, 11 passed (pass_fraction 0.153)**
- By asset class: equity 11/36, **crypto 0/36 (decisive fail)**
- By vol regime: low 6/24, mid 5/24, **high 0/24**
- Best cell: QQQ, min_hold_days=10/trend_window=100, mid-vol regime, Sharpe 1.70

## Single-config validators (min_hold_days=10, trend_window=100)

| Symbol | Trades | Sharpe (full) | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|
| QQQ | 45 | 0.798 **FAIL** (thr 1.0) | 0.276 **FAIL** (thr 0.25) | 0.710 PASS | 0.75 pass_fraction PASS | 0.168 PASS |
| SPY | 52 | 0.559 **FAIL** (thr 1.0) | 0.221 PASS | 0.442 **FAIL** (thr 0.5) | 0.75 pass_fraction PASS | 0.182 PASS |

## Decision: REJECTED

The min_hold_days fix worked as designed — trade count dropped from 442 to
45-52 (roughly a 9x reduction) and net-of-cost Sharpe improved
substantially (from -0.089 to 0.71/0.44). However, the predecessor's raw
Sharpe near-miss did NOT survive the fix: forcing a minimum 10-day hold
before any exit check (including the uptrend-break exit) means losing
trades that should have exited early now ride out the full min-hold window,
which is exactly what appears to have hurt QQQ's max drawdown (0.276,
newly failing the 0.25 cap — the predecessor's MDD was never disclosed as a
failure point) and dragged both symbols' full-sample Sharpe below the
predecessor's own near-miss level. Net result: TC-survival is fixed but a
new MDD failure (QQQ) and Sharpe degradation (both) replace it — not a net
improvement. Crypto failed all 36 grid cells decisively, same as the
predecessor. The grid's isolated mid-vol best cell (Sharpe 1.70) is again a
regime-concentration artifact (0/24 in the high-vol tercile) that does not
generalize to the full sample.

This confirms overtrading was not the ONLY problem with the middle-line
pullback construction -- forcing a longer minimum hold degrades exit
discipline just as much as high-frequency re-entry degraded costs. No
further Keltner-midline-pullback variant recommended; this closes out the
Keltner Channel family (breakout, mean-reversion, squeeze x2, pullback,
pullback+min-hold — 6 variants now tested) for this repo's scope.

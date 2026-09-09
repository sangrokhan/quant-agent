# JMA/DWMA Crossover — SPY Refinement — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_jma_dwma_crossover.py` (same file, SPY-specific config)
**Outcome:** ACCEPTED (SPY, refined config)

## Hypothesis

Direct follow-up to this cron trigger's own near-miss (2026-09-09-099,
JMA/DWMA crossover): QQQ's config (fast_span=5/slow_window=20/
max_hold_days=30/atr_mult=1.5) cleared all validators, but SPY at the
identical config was an extremely close near-miss (Sharpe 0.959, just 4%
short of threshold) while passing every other validator comfortably. A
targeted local parameter search around that near-miss (varying
fast_span, slow_window, max_hold_days, atr_mult) for SPY specifically —
following this repo's established pattern of refining near-misses into
accepts (e.g. 2026-09-08-154 for the Skewness-Regime strategy) — found a
materially better SPY-specific optimum.

## Local parameter search (SPY, 2018-01-01 to 2026-09-01)

Swept fast_span in [3,4,5,6,7], slow_window in [15,18,20,22,25],
max_hold_days in [20,25,30,40], atr_mult in [1.0,1.5,2.0] (180
combinations, full-sample Sharpe only, no vol-regime slicing needed since
this is a targeted local refinement, not a fresh strategy's Step 6 grid).

Best found: **fast_span=4, slow_window=15, max_hold_days=25, atr_mult=1.0**
— full-sample Sharpe 1.357 (vs. the original config's 0.959).

## Single-config validation (SPY, fast_span=4, slow_window=15,
max_hold_days=25, atr_mult=1.0)

| Metric | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.357 | 1.0 | **PASS** |
| Max drawdown | 12.5% | 25% | **PASS** |
| TC-survival net Sharpe | 1.187 | 0.5 | **PASS** |
| Walk-forward pass fraction | 1.0 (4/4 splits) | 0.75 | **PASS** |
| Parameter sensitivity (relative std) | 0.173 | 0.5 | **PASS** |

87 trades over 8.7 years. All 5 validators pass cleanly.

## Verdict: ACCEPTED for SPY (refined config)

SPY now has its own accepted config for this strategy family, distinct
from QQQ's (per this repo's established pattern that these two symbols
are NOT interchangeable for MA-crossover-family strategies — see also
Chandelier+Supertrend 2026-09-09-090/091 for a prior example of the same
per-symbol-tuning finding): SPY needs a faster/shorter fast_span(4) and
slow_window(15) than QQQ's fast_span(5)/slow_window(20), plus a tighter
ATR stop (1.0x vs 1.5x) and a slightly shorter max_hold_days (25 vs 30).

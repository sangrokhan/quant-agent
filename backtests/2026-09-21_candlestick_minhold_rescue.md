# Candlestick OR-Gate min_hold_days Turnover-Reduction Rescue — Backtest Report

**Date:** 2026-09-21
**Strategy file:** `strategies/2026-09-21_combined_candlestick_meanrev.py` (added `min_hold_days` param)
**Rescue of:** 2026-09-21-269 (combined candlestick OR-gate, SPY TC-survival near-miss 0.455<0.5)

## Hypothesis

The prior iteration's SPY config (max_hold_days=5) passed Sharpe/MDD but
narrowly failed transaction-cost-survival due to high turnover. Adding a
`min_hold_days` gate (ignore exit signal for N days post-entry, same
rescue pattern already validated for the XLP range-band strategy,
2026-09-21-266) should cut trade count and improve net-of-cost Sharpe
without materially hurting the raw edge.

## Grid test (Step 6)

`param_grid={"max_hold_days": [5,10,15], "min_hold_days": [1,2,3,4]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- Overall pass_fraction: 0.271 (39/144 cells)
- By asset class: equity 39/72 (0.54), crypto 0/72 (decisive reject, confirms 2026-09-21-269)
- Best cell: QQQ, max_hold_days=5/min_hold_days=4, low-vol regime, Sharpe 1.818
- min_hold_days=4 consistently the best value across max_hold_days settings for QQQ

## Single-config validation (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival |
|---|---|---|---|---|
| QQQ | max_hold=5, min_hold=4 | **0.993** (FAIL, thr 1.0, near-miss) | 0.136 (PASS) | **0.609** (PASS) |
| SPY | max_hold=5, min_hold=2 | 0.982 (FAIL, thr 1.0, near-miss) | 0.123 (PASS) | 0.430 (FAIL, near-miss) |

Additional QQQ configs tried: (10,4) Sharpe 0.905/TC 0.609; (10,3) Sharpe
0.651/TC 0.364; (15,4) Sharpe 0.798/TC 0.525. Best QQQ full-sample Sharpe
across all tried configs is (5,4) at 0.993 -- extremely close to but still
under the 1.0 threshold.

## Decision: **REJECT (both symbols near-miss)**

The `min_hold_days` gate successfully fixed the transaction-cost-survival
failure mode for QQQ (0.609 now passes; previously not computed for QQQ
standalone in 2026-09-21-269's config, but the mechanism generalizes) but
QQQ's raw Sharpe is now the binding constraint at 0.993, just 0.007 below
the 1.0 threshold -- a decisive-enough gap not to force a pass. SPY remains
a double near-miss (Sharpe 0.982, TC-survival 0.430). Crypto is a
decisive 0/72 reject across the whole min_hold_days sweep, confirming
2026-09-21-269's finding that this equity-mean-reversion-tuned pattern set
does not transfer to crypto. No further rescue attempted this iteration
(diminishing returns from more parameter search on an already-narrow
near-miss); strategy/report files kept as a record.

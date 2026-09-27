# Volume-Confirmed Pivot Resistance Breakout (2026-09-28)

**Hypothesis:** LuxAlgo's "Support and Resistance Levels with Breaks"
requires a volume-oscillator confirmation on a pivot-resistance breakout
before tagging it as genuine. Source:
https://www.luxalgo.com/library/indicator/support-and-resistance-levels-with-breaks/
(read 2026-09-28 via browser_exec). Distinct from Bill Williams Fractals
(2026-09-04-134, identical pivot geometry, no volume gate).

## Step 6 grid summary (left_bars x {5,10}, right_bars x {5,10},
volume_threshold x {0.0,5.0,10.0}; equity QQQ/SPY + crypto BTC/ETH;
vol_regime_splits=3; 144 cells)

- pass_fraction: 0.368 (53/144)
- by_asset_class: equity 24/72, crypto 29/72
- by_vol_regime: low 33/48, mid 18/48, high 2/48
- best_cell: left_bars=10, right_bars=5, volume_threshold=0.0, QQQ,
  low-vol regime, Sharpe 2.23

## Step 7 full-sample validators (config: left_bars=10, right_bars=5,
vo_fast=5, vo_slow=10, volume_threshold=0.0, max_hold_days=30)

| Symbol | Trades | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|
| QQQ | 42 | 0.49 FAIL | 0.13 PASS | 0.39 FAIL | 1.00 PASS | 2.24 FAIL |
| SPY | 49 | 0.41 FAIL | 0.08 PASS | 0.24 FAIL | 0.75 PASS | 0.22 PASS |
| BTC/USDT | 2102 | 0.22 FAIL | 0.32 FAIL | 0.01 FAIL | 1.00 PASS | 0.13 PASS |
| ETH/USDT | 2100 | 0.33 FAIL | 0.43 FAIL | 0.07 FAIL | 1.00 PASS | 0.14 PASS |

Despite the promising grid pass_fraction (0.368, driven almost entirely by
the low-vol tercile), the full-sample Sharpe fails at every parameter
setting tested for every symbol -- a classic low-vol-tercile artifact
pattern this repo has seen repeatedly (e.g. ROC-of-ROC 2026-09-28-009,
Retest & Break Setup 2026-09-28-010). Crypto additionally decisively fails
MDD/TC-survival on adequate sample sizes.

## Decision: **REJECT** across all symbols -- full-sample Sharpe fails at
the grid's best config on every symbol despite a superficially reasonable
grid pass_fraction; equity's edge is confined to the low-vol tercile and
does not generalize. Strategy file kept for the record as a rejected
attempt.

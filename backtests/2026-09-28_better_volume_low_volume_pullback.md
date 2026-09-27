# Better Volume Classifications "Low Volume" Pullback Buy (2026-09-28)

**Hypothesis:** LuxAlgo's Better Volume Classifications benchmarks raw
volume, volume x range, and volume / range against rolling extremes.
Source: https://www.luxalgo.com/library/indicator/better-volume-classifications/
(read 2026-09-28 via browser_exec). A "Low Volume" print (today's volume is
the window's quietest, source: "the classic test print that supports
continuation on a pullback") on a down-close day within an SMA uptrend
marks a low-conviction dip. A "Climax Down" print (volume x range is the
window's most extreme, on a down-close day) while long triggers a
defensive exit (capitulation/exhaustion signature).

## Step 6 grid summary (trend_window x {30,50,70}, lookback x {15,20,30},
max_hold_days x {15,20,30}; equity QQQ/SPY + crypto BTC/ETH;
vol_regime_splits=3; 324 cells)

- pass_fraction: 0.210 (68/324)
- by_asset_class: equity 59/162, crypto 9/162
- by_vol_regime: low 45/108, mid 8/108, high 15/108
- best_cell: trend_window=50, lookback=30, max_hold_days=30, QQQ, low-vol
  regime, Sharpe 2.85

## Step 7 full-sample validators (config: trend_window=50, lookback=30,
max_hold_days=30)

| Symbol | Trades | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|
| QQQ | 34 | 1.44 PASS | 0.119 PASS | 1.36 PASS | 1.00 PASS | 0.225 PASS |
| SPY | 43 | 0.56 FAIL | 0.108 PASS | 0.44 FAIL | 0.75 PASS | 0.426 PASS |
| BTC/USDT | 1090 | 0.001 FAIL | 0.381 FAIL | -0.07 FAIL | 0.50 FAIL | 0.726 FAIL |
| ETH/USDT | 1045 | 0.11 FAIL | 0.455 FAIL | -0.01 FAIL | 0.75 PASS | 0.204 PASS |

Crypto decisively rejected (near-zero Sharpe, MDD 0.38-0.46, negative
TC-survival) on 1h-bar overtrading (1045-1090 trades). SPY is a near-miss
(Sharpe 0.56, TC-survival 0.44 -- both below threshold but not decisively).

## Decision: **ACCEPT for equity (QQQ only)** -- all 5 validators pass.
SPY near-miss reject; crypto decisively rejected. Consistent with this
repo's frequent pattern of QQQ-only acceptance for pullback-style entries
with a moderate trade count.

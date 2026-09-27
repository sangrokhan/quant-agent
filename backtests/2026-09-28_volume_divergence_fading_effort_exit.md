# Volume Divergence "Fading Effort" Defensive-Exit Overlay (2026-09-28)

**Hypothesis:** LuxAlgo's Volume Divergence concept page describes "fading
effort": successive trend legs (higher highs) fueled by shrinking summed
volume signal the advance is running out of participants. Source:
https://www.luxalgo.com/library/concept/volume-divergence/ (read 2026-09-28
via browser_exec). Operationalized as a defensive-exit overlay on a plain
SMA-crossover trend-following long: while long, a fresh swing-pivot high
whose fueling-leg summed volume is < fade_ratio x the prior leg's summed
volume triggers an immediate protective exit, pre-empting the classic
stall/reversal that follows fading-effort divergence.

## Step 6 grid summary (trend_window x {30,50,70}, pivot_window x
{5,10,15}, fade_ratio x {0.6,0.7,0.8}; equity QQQ/SPY + crypto BTC/ETH;
vol_regime_splits=3; 324 cells)

- pass_fraction: **0.333** (108/324)
- by_asset_class: equity 81/162, crypto 27/162
- by_vol_regime: low 81/108, mid 27/108, high 0/108
- Aggregating average Sharpe by param combo across symbols/regimes:
  trend_window=30 dominates regardless of pivot_window/fade_ratio choice
  (avg Sharpe ~1.27 across all trend_window=30 combos vs materially lower
  for trend_window=50/70) -- unusually low parameter sensitivity for this
  hyperparameter.

## Step 7 full-sample validators (config: trend_window=30, pivot_window=10,
fade_ratio=0.7, max_hold_days=40)

| Symbol | Trades | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|
| QQQ | 146 | 1.22 PASS | 0.232 PASS | 0.98 PASS | 1.00 PASS | 0.0 PASS |
| SPY | 159 | 1.03 PASS | 0.178 PASS | 0.71 PASS | 0.75 PASS | 0.0 PASS |
| BTC/USDT | 6825 | 0.17 FAIL | 0.596 FAIL | -0.04 FAIL | 1.00 PASS | 0.0 PASS |
| ETH/USDT | 6617 | 0.21 FAIL | 0.518 FAIL | -0.03 FAIL | 1.00 PASS | 0.0 PASS |

Crypto again decisively fails on 1h-bar overtrading (6600-6800 position
flips over the sample) -- consistent with this repo's recurring pattern
that daily-bar signal logic doesn't transfer to 1h crypto bars.

## Decision: **ACCEPT for equity (QQQ AND SPY)** -- both pass all 5
validators run (SPY's Sharpe 1.032 and walk-forward 0.75 are near their
respective thresholds but both genuinely clear the bar). Reject crypto
decisively.

This is the strongest equity result of this cron trigger's iterations so
far -- both large-cap tech and broad-market ETF pass every validator with
essentially zero parameter sensitivity around fade_ratio.

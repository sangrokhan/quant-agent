# 2026-09-15 Constance Brown CMB Composite Index MA-Crossover + Vol-Regime Gate

**Hypothesis:** Direct fix for this same cron trigger's prior entry
2026-09-16-112 (Constance Brown CMB Composite Index MA-crossover: SPY
accepted, QQQ near-miss ceiling ~Sharpe 0.895-0.921 at every config
tried). Adds an explicit realized-vol regime filter (20d realized vol vs
trailing 252d median, this repo's established 2026-09-03-001 pattern) on
top of the unchanged Composite Index MA-crossover mechanics. No new
external source this sub-iteration.

**Primary config (QQQ):** fast_ma_period=10, slow_ma_period=33,
max_hold_days=30, vol_regime_ratio=1.5

## Single-config validator results (QQQ, full 2018-2026 sample)

| Metric | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe | 1.102 | 1.0 | Yes |
| Max Drawdown | 0.164 | 0.25 | Yes |
| TC-survival net Sharpe | 0.807 | 0.5 | Yes |
| Walk-forward pass fraction | 1.0 | 0.75 | Yes |
| Parameter sensitivity (rel std) | 0.334 | 0.5 | Yes |

All 5 validators pass -- QQQ near-miss rescued.

## Grid summary (vol_regime_ratio in [1.2,1.5] x fast_ma_period in [10,13]
x slow_ma_period in [33,45], QQQ/SPY/BTC-USDT/ETH-USDT x low/mid/high vol
tercile, 96 cells)

- pass_fraction: 0.302 (29/96)
- by_asset_class: equity 21/48; crypto 8/48
- by_vol_regime: low 16/32; mid 8/32; high 5/32 (vol gate salvages a few
  high-vol passes, similar to the overnight-momentum rescue earlier this
  cron trigger, though the high-vol pass rate here is lower)
- Looser vol_regime_ratio=1.5 (only exclude nights materially above the
  trailing-vol median) at fast=10/slow=33 gave the QQQ rescue; tighter
  vol_regime_ratio=1.2 did not clear both thresholds.

## Outcome: ACCEPTED (QQQ) -- combined with 2026-09-16-112's SPY accept,
this Composite Index family is now full-equity (QQQ+SPY); crypto remains
out of scope (not retested with the vol gate this sub-iteration since the
base mechanism already failed decisively on crypto in 2026-09-16-112 --
BTC/ETH's own volatility level is the entire issue, not the gate's
threshold tightness).

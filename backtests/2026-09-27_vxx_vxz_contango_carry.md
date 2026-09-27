# VXX/VXZ Contango Carry — rejected

**Hypothesis:** short-front-month/long-mid-curve VIX-ETN pair (short VXX,
long VXZ) harvests the VIX futures curve's typical negative roll yield
during contango/calm regimes. Source:
https://wolfx.trade/whitepaper/vix-carry (WOLFX Research whitepaper, cites
Eraker & Wu 2017 JFE, Alexander & Korovilas 2013 JAI, Carr & Wu 2009 RFS).
First VXX/VXZ pair-carry strategy in this repo.

**Strategy file:** `strategies/2026-09-27_vxx_vxz_contango_carry.py`

## Grid test

`param_grid={entry_contango:[0.03,0.05,0.08], max_hold_days:[30,60,90]}`,
symbols equity=[VXX] (VXZ/SPY fetched internally as the pair legs),
vol_regime_splits=3, 2018-02-01..2026-09-01. Contango proxy redefined from
the source's raw price-ratio (VXX/VXZ absolute unit prices are not directly
comparable across ETN products with different inception NAVs -- biased,
non-stationary) to a 60-day trailing cumulative-return spread
(`ret_60(VXZ) - ret_60(VXX)`), which produces a sensible ~[-0.1, +0.3]
range matching the intended semantics.

- pass_fraction 0.296 (8/27), ALL 8 passing cells in the LOW-vol tercile
  (8/9 low, 0/9 mid, 0/9 high) -- an even more concentrated single-regime
  pattern than most near-misses in this repo.
- Best cell Sharpe 1.391 (entry_contango=0.03, max_hold_days=90, low-vol
  tercile only).

## Full-sample / parameter-search check

A targeted local search (`entry_contango in [0.02,0.03,0.05,0.08,0.1] x
exit_contango in [0.0,0.01,0.02] x max_hold_days in [30,60,90,120] x
emergency_vol_mult in [1.5,1.8,2.2]`, 180 combos) on VXX/VXZ/SPY full-sample
2018-2026 found **no configuration with a positive full-sample Sharpe** --
best achievable was -0.036 (near the entry threshold that produced the
grid's best low-vol-tercile cell). At the grid's own best config
(entry_contango=0.03, max_hold_days=90): full-sample Sharpe -0.083, total
return -12.8% over the full period, 51 trades.

Unlike this repo's typical "near-miss, narrow-but-honest regime" accepts
(where a strategy clears Sharpe>=1.0 full-sample or at least a clean
single-regime edge that's separately validated), here the isolated
low-vol-tercile grid cells do NOT translate into a viable full-sample
strategy even restricted to that regime via the strategy's own calm-regime
gate -- the gate is already active in the full-sample run and it still
loses money overall. This suggests the grid's tercile-level pass is a
narrow-window artifact (a few favorable low-vol stretches) rather than a
durable regime-conditional edge.

## Outcome

**Rejected** — no full-sample-viable configuration found despite a 180-combo
local search; grid-level "pass" is concentrated in a narrow low-vol tercile
that doesn't hold up once the calm-regime gate (which already restricts
trading to low-vol conditions) is applied over the whole sample.

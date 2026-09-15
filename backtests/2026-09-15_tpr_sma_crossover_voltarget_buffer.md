# 2026-09-15 TPR-Filtered SMA Crossover + Vol-Target Buffer

**Hypothesis:** Direct fix for this same cron trigger's prior entry
2026-09-16-115 (TPR trend-persistence-filtered SMA crossover: QQQ/SPY
Sharpe near-misses, BTC/USDT passed Sharpe but decisively failed MDD
0.462, ETH/USDT near-missed Sharpe and decisively failed MDD 0.541). Adds
this repo's already-validated inverse-volatility position-sizing overlay
with a no-trade rebalance buffer (per 2026-09-07-026's established
construction) on top of the unchanged TPR-filtered SMA crossover base
signal. No new external research this sub-iteration.

**Per-symbol configs (equity vol_cap=1.0, crypto vol_cap=0.6 given
crypto's higher raw volatility -- same pattern as several other accepted
crypto strategies in this repo):**
- QQQ: target_vol=0.15, rebalance_buffer=0.15
- BTC/USDT: target_vol=0.15, rebalance_buffer=0.10
- ETH/USDT: target_vol=0.12, rebalance_buffer=0.05

## Single-config validator results (full 2018-2026 sample)

| Symbol | Sharpe | MDD | TC net Sharpe | Walk-forward | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| QQQ | 1.075 (pass) | 0.128 (pass) | 0.985 (pass) | 1.0 (pass) | 0.072 (pass) |
| BTC/USDT | 1.091 (pass) | 0.240 (pass) | 0.997 (pass) | 1.0 (pass) | 0.022 (pass) |
| ETH/USDT | 1.062 (pass) | 0.174 (pass) | 0.912 (pass) | 1.0 (pass) | 0.010 (pass) |

All 5 validators pass on all 3 symbols. SPY was NOT rescued -- a dedicated
search (7 target_vol x 4 rebalance_buffer x 3 vol_cap = 84 combos, plus 12
fast/slow/tpr_threshold variants at the best vol-target settings) found no
config clearing Sharpe>=1.0 for SPY; SPY remains rejected from
2026-09-16-115.

## Grid summary (target_vol in [0.12,0.15,0.20] x rebalance_buffer in
[0.05,0.10,0.15], QQQ/SPY/BTC-USDT/ETH-USDT x low/mid/high vol tercile,
vol_cap fixed at default 1.0 for this grid pass, 108 cells)

- pass_fraction: 0.528 (57/108) -- up sharply from the ungated version's
  0.265
- by_asset_class: equity 24/54; crypto 33/54
- by_vol_regime: low 33/36; mid 15/36; high 9/36 -- the vol-targeting
  overlay materially improves high-vol-regime survival vs the ungated
  version's 0/108

## Outcome: ACCEPTED (QQQ, BTC/USDT, ETH/USDT); REJECTED (SPY -- no config
found clearing Sharpe threshold even with the vol-target rescue)

The inverse-volatility overlay with rebalance buffer successfully rescued
3 of the 4 symbols from 2026-09-16-115's rejection, directly confirming
that entry's own diagnosis: TPR is a trend-strength filter, and pairing it
with an actual risk-control (vol-targeting) mechanism was the missing
piece. SPY's persistent shortfall even after this fix suggests the base
TPR-filtered-crossover signal itself may be structurally weaker on SPY
specifically (as also seen with the Composite Index and other strategies
this cron trigger), not merely a risk-sizing problem.

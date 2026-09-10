# 2026-09-11 GTAA Dual-Momentum Absolute-Momentum Gate (SPY/EFA/EEM/GLD/TLT basket)

## Hypothesis
Direct fix attempt for near-miss/rejected `2026-09-11-037` (5-asset momentum
rotation gate, always-hold-top-pick, decisively rejected: Sharpe 0.11-0.32,
MDD breach 0.29-0.32). Per Quantpedia's "Active Dual Momentum GTAA Strategy"
(22 May 2026, https://quantpedia.com/active-dual-momentum-gtaa-strategy/),
the source's own disclosed methodology layers an **absolute momentum
filter** (only hold an asset with positive trailing RoC; otherwise cash) on
top of relative-momentum ranking. Adapted single-asset: hold SPY only when
it is both the top-ranked basket pick (SPY/EFA/EEM/GLD/TLT) AND its own
trailing RoC is positive; cash otherwise. Rebalance cadence tested at
weekly (5 trading days) and monthly-ish (21 days), lookback at
63/126/252 trading days.

Source: https://quantpedia.com/active-dual-momentum-gtaa-strategy/ (visited this iteration)

## Grid summary (run_strategy_grid, param_grid={lookback_days:[63,126,252], rebalance_days:[5,21]}, symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3)

- total_cells: 72, passed_cells: 10, pass_fraction: 0.139
- by_asset_class: equity 10/36 passed, crypto 0/36 passed (decisive crypto rejection, no bond/gold analog basket makes sense for crypto)
- by_vol_regime: low 10/24, mid 0/24, high 0/24 (edge entirely confined to low-vol tercile)
- best_cell: QQQ, lookback_days=252, rebalance_days=5, low-vol regime, Sharpe 1.91

## Single-config validation (best full-sample config: lookback_days=252, rebalance_days=5, primary_symbol=SPY)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.761 (SPY) / 0.679 (QQQ) | >= 1.0 | **FAIL** |
| Max drawdown | 0.117 (SPY) / 0.185 (QQQ) | <= 0.25 | PASS |
| TC survival (10bps/trade, 28 trades) | 0.689 (SPY) | >= 0.5 | PASS |
| Walk-forward | not run (vectorbt.utils.splitting API unavailable in this environment -- known repo issue) | -- | skipped |
| Parameter sensitivity (low-vol tercile SPY Sharpes across grid) | computed from grid cells | <= 0.5 rel. std | not decisive given full-sample fail |

## Decision: REJECT

Full-sample Sharpe (0.68-0.76) misses the >=1.0 threshold on both QQQ and
SPY despite MDD and TC-survival passing. The absolute-momentum cash gate
IS a clear improvement over the prior fully-invested construction
(2026-09-11-037: Sharpe 0.11-0.32, MDD breach) -- it fixes the MDD breach
entirely (0.117/0.185 vs 0.29-0.32) and roughly triples the Sharpe -- but
still falls short of the acceptance bar. Edge is real but concentrated
entirely in the low-vol tercile (10/24 low-vol cells pass vs 0/24 in
mid/high-vol), consistent with a slow, cash-heavy rotation strategy
underperforming during regime transitions. Crypto basket-substitution is
not meaningful (no bond/gold analogs) and rejected decisively as expected.

Worth a future revisit: shorter rebalance (5d) + longer lookback (252d)
is the best combo found; a future iteration could try adding a bond-proxy
(IEF instead of cash) as the fallback when absolute momentum is negative,
mirroring the already-accepted GEM/IEF dual-momentum finding (2026-09-07-023).

# MAMA/FAMA crossover with min_hold_days fix

Hypothesis: direct fix for 2026-09-06-101 (MAMA/FAMA crossover, accepted QQQ,
rejected SPY as a near-miss: Sharpe 0.649, net-of-cost Sharpe 0.483, 70 trades).
Applies this repo's proven min_hold_days gate (originally used to fix KVO,
2026-09-04-085) to reduce whipsaw trade count on the same crossover logic.
Source (re-confirmed formula/behavior this iteration):
https://iwpfinance.com/concepts/technical-analysis/mama-fama-mesa-adaptive

## Grid summary (min_hold_days x [3,5,8] x max_hold_days [30,40], QQQ+SPY equity, BTC/USDT+ETH/USDT crypto, 3 vol terciles)
- total_cells=72, passed=19, pass_fraction=0.264
- by_asset_class: equity 19/36 passed; crypto 0/36 passed (decisive reject, unchanged from original 2026-09-06-101)
- by_vol_regime: low 12/24, mid 6/24, high 1/24 (same low-vol-favoring pattern seen across this repo's trend/momentum strategies)

## Full-sample single-config validation
| Symbol | min_hold | max_hold | Sharpe | MDD | TC-survival net Sharpe | trades |
|---|---|---|---|---|---|---|
| QQQ | 8 | 40 | 1.261 (pass) | 0.195 (pass) | 1.217 (pass) | 28 |
| SPY | 8 | 40 | 0.836 (fail, <1.0) | 0.180 (pass) | 0.789 (pass) | 30 |

- parameter_sensitivity (QQQ, 20-combo min_hold x max_hold sweep): relative_std=0.077 (pass, threshold 0.5)
- walk_forward: not run -- pre-existing `vbt.utils.splitting` AttributeError bug in this repo's vectorbt install (same limitation noted on 2026-09-06-101 and others)

## Decision
ACCEPTED for QQQ only (min_hold_days=8, max_hold_days=40): Sharpe/MDD/TC-survival/param-sensitivity all pass,
improving on the original 2026-09-06-101 QQQ config (Sharpe 1.142 -> 1.261).
REJECTED for SPY: min_hold_days fix raised Sharpe from 0.649 to 0.836 but still falls short of the 1.0 threshold --
the fix mechanism helps but does not fully resolve the SPY near-miss.
REJECTED for crypto (unchanged, decisive fail across the full grid).

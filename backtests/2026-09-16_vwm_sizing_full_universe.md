# VWM Full-Universe Extension (2026-09-16-058)

## Hypothesis
Volume Weighted Momentum (VWM = SMA(smooth_period, (Close-Close[mom_period ago])*Volume)),
per https://alfatactix.com/academy/indicators/volume-weighted-momentum, previously accepted
QQQ-only in this repo (2026-09-15-011; SPY/crypto not yet tested). This sub-iteration extends
the identical VWM continuous-sizing-dial strategy (`strategies/2026-09-15_vwm_sizing_sma_trend.py`)
to SPY and to crypto (BTC/USDT, ETH/USDT) via the repo's standard leverage-cap-aware retune
(reduce `leverage_cap`/`base_exposure` for crypto). No new external research this sub-iteration.

## Grid summary (Step 6)
`param_grid={mom_period:[10,14], smooth_period:[14,20], sensitivity:[0.5,0.7], deadband:[0.2,0.3]}`,
symbols equity {QQQ, SPY} + crypto {BTC/USDT, ETH/USDT}, vol_regime_splits=3.

- total_cells: 192, passed_cells: 81, pass_fraction: 0.4219
- by_asset_class: equity 48/96, crypto 33/96
- by_vol_regime: low 57/64, mid 23/64, high 1/64
- best_cell: SPY, mom_period=10/smooth_period=14/sensitivity=0.7/deadband=0.3, low-vol Sharpe 2.906

## Best-config validators (Step 7)

| Symbol | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|
| QQQ | 1.121 | 0.140 | 0.812 | 0.75 | 0.073 | Yes |
| SPY | 1.040 | 0.095 | 0.627 | 0.75 | 0.033 | Yes |
| BTC/USDT | 1.268 | 0.113 | 1.044 | 1.00 | 0.092 | Yes |
| ETH/USDT | 1.092 | 0.152 | 0.923 | 1.00 | 0.015 | Yes |

Configs:
- QQQ: mom_period=10, smooth_period=14, sensitivity=0.7, deadband=0.30, base_exposure=0.4, leverage_cap=1.0
- SPY: mom_period=10, smooth_period=14, sensitivity=0.7, deadband=0.30, base_exposure=0.4, leverage_cap=1.0
- BTC/USDT: mom_period=14, smooth_period=14, sensitivity=0.4, deadband=0.20, base_exposure=0.2, leverage_cap=0.3
- ETH/USDT: mom_period=10, smooth_period=14, sensitivity=0.4, deadband=0.20, base_exposure=0.2, leverage_cap=0.25

## Outcome
Accepted (full universe): all 5 validators pass on QQQ, SPY, BTC/USDT, ETH/USDT.

Source: https://alfatactix.com/academy/indicators/volume-weighted-momentum (already visited
2026-09-15, VWM formula already documented in this repo from id 2026-09-15-011; no new URL
fetched this sub-iteration).

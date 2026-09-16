# Backtest report: OU half-life z-score continuous sizing dial

**Strategy file:** `strategies/2026-09-17_ou_halflife_zscore_sizing_dial.py`

## Hypothesis

Per this repo's own already-confirmed OU/AR(1) half-life formula
(originally sourced from https://quanterlab.com/articles/stochastic-ou-process,
strategies/2026-09-07_ou_halflife_zscore_meanrev.py) and reconfirmed this
iteration via https://algodrill.app/mean-reversion-strategy ("Position
scaling improves on binary entry ... approximates the OU strategy's optimal
policy under Gaussian assumptions" — AlgoDrill Module 8), reframe the OU
half-life-gated z-score (previously only tested as a binary {0,1}
entry/exit trigger, both prior attempts near-miss/rejected on parameter
sensitivity: 2026-09-07-012, 2026-09-12-157) as a CONTINUOUS exposure dial
via tanh(-z), gated by the same half-life 5-30 bar tradable-regime filter,
held with a no-trade deadband.

## Grid test summary (Step 6)

`param_grid={"sensitivity": [0.4, 0.6, 0.8], "leverage_cap": [0.5, 1.0]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells: 72, passed_cells: 14, **pass_fraction: 19.4%**
- by_asset_class: equity 14/36 passed; **crypto 0/36 passed**
- by_vol_regime: low 6/24; mid 8/24; **high 0/24**
- best_cell: QQQ, low-vol regime, sensitivity=0.4/leverage_cap=0.5, Sharpe 2.36
- worst_cell: BTC/USDT, mid-vol regime, Sharpe -0.94

## Single-config validators (best grid config: sensitivity=0.4, leverage_cap=0.5), full sample 2019-2026

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **FAIL** 0.10 | **FAIL** -0.04 |
| Max Drawdown (<=0.25) | pass 0.213 | pass 0.202 |
| TC survival (net Sharpe >=0.5, 5bps/trade) | **FAIL** -0.10 (208 trades) | **FAIL** -0.29 (235 trades) |
| Walk-forward (4-split manual date-split fallback, vbt RangeSplitter broken in installed vbt==1.1.0) | **FAIL** 0.50 (2/4 splits positive) | **FAIL** 0.50 (2/4 splits positive) |
| Parameter sensitivity (relative_std <=0.5, sensitivity in [0.3..0.7]) | pass 0.202 | **FAIL** 1.76 |

## Decision: REJECTED

Full-sample Sharpe and TC-survival decisively fail on both equity symbols
despite the grid's headline pass_fraction — the grid's per-vol-regime
cells (each covering ~1/3 of the full sample) show good Sharpe locally
(best cell 2.36) but the tanh-dial + deadband construction does not hold
up when stitched across regimes/full sample; walk-forward confirms this
(only 2/4 splits positive on both symbols). SPY additionally fails
parameter sensitivity outright (relative_std 1.76, wildly unstable across
sensitivity values). Crypto rejected decisively (0/36 grid cells, high-vol
regime universally fails 0/24). This closes out the "continuous sizing
dial" rescue pattern for this specific OU half-life construction — unlike
many other oscillators in this repo where the sizing-dial reframing
rescued a binary near-miss, here it does not fix the underlying issue
(the OU half-life regime gate itself is unstable/discontinuous across
regimes, which a continuous exposure multiplier does not smooth out).

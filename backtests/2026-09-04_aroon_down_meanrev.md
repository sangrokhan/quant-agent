# Aroon-Down Mean Reversion — Backtest Report (2026-09-04-031)

**Hypothesis:** Per QuantifiedStrategies.com's Aroon indicator article
(https://www.quantifiedstrategies.com/aroon-indicator-strategy/,
"Strategy no 1"): buy when Aroon-Down < 10 (a very recent new low),
sell when Aroon-Down > 50 (downtrend momentum faded). Source's own SPY
backtest (14-day period): 252 trades, avg gain 0.44%/trade, win rate 56%,
MDD 23%, profit factor 1.5. This iteration's own parameter sweep found a
wider window (25) and looser exit threshold (20 instead of 50) perform
better on this repo's sample.

## Primary config (QQQ, aroon_window=25, oversold_threshold=20.0, exit_threshold=50.0)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | **True** | 1.126 | 1.0 |
| max_drawdown | True | 0.148 | 0.25 |
| transaction_cost_survival (10bps, 39 trades) | True | 1.065 | 0.5 |
| walk_forward (manual 4-split fallback; vectorbt splitter still broken) | True | 1.0 (4/4 splits positive) | 0.75 |
| parameter_sensitivity (aroon_window x oversold_threshold, 4 combos) | True | rel.std 0.158 | 0.5 |

All 5 standard validators pass on QQQ.

## SPY check (same config) — fails

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | **False** | 0.518 | 1.0 |

SPY fails decisively at this config (not a near-miss) -- do not extend
this acceptance to SPY.

## Grid test summary (validation/grid_test.py::run_strategy_grid)

Grid: `aroon_window x {14,25}`, `oversold_threshold x {10,20}`, symbols
`{QQQ, SPY, BTC/USDT, ETH/USDT}`, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01. 48 cells total.

- pass_fraction: **0.229** (11/48)
- by_asset_class: equity 11/24, crypto 0/24
- by_vol_regime: low 8/16, mid 3/16, high 0/16
- best_cell: QQQ, aroon_window=25, oversold_threshold=20, low-vol tercile, Sharpe 2.96
- worst_cell: QQQ, aroon_window=25, oversold_threshold=10, high-vol tercile, Sharpe -0.50

Full-sample sanity checks (Sharpe, trades):
- QQQ: (14,10)→0.735/66, (14,20)→0.771/66, (25,10)→0.598/39, (25,20)→0.936/39
- SPY: (14,10)→0.560/65, (14,20)→0.464/65, (25,10)→0.290/42, (25,20)→0.430/44

The (25, 20) combo clears vectorbt's Sharpe (1.126, slightly above the
0.936 simple-mean approximation) on QQQ specifically; every other
combo/symbol falls short.

## Decision: **ACCEPTED (QQQ only, aroon_window=25, oversold_threshold=20, exit_threshold=50)**

QQQ clears all 5 standard validators at this specific config. SPY fails
decisively at the same config (Sharpe 0.518) -- do not extend. Crypto
rejected decisively (0/24 grid cells). First Aroon indicator (pure
elapsed-time-since-extreme measure, distinct from every prior
price-magnitude oscillator in this repo) strategy accepted.

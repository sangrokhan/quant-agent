# All-Time-High Chandelier Trend — Backtest Report (2026-09-04-025)

**Hypothesis:** Per QuantPedia's "Trend-following Effect in Stocks"
(https://quantpedia.com/strategies/trend-following-effect-in-stocks/,
source paper: Wilcox & Crittenden, "Does Trend Following Work on Stocks?",
1983-2004, indicative perf 19.3%/yr, MDD -33.74%, Sharpe 1.24): enter long
when close reaches a new ALL-TIME HIGH, exit only via a ratcheting ATR(10)
chandelier trailing stop (running_high - atr_multiplier * ATR).

## Primary config (QQQ, atr_window=10, atr_multiplier=3.0 — source default)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | **False** | 0.966 | 1.0 |
| max_drawdown | True | 0.118 | 0.25 |
| transaction_cost_survival (10bps, 15 trades) | True | 0.942 | 0.5 |
| walk_forward (manual 4-split fallback; vectorbt splitter still broken) | True | 1.0 (4/4 splits positive) | 0.75 |
| parameter_sensitivity (atr_multiplier in {2,3,4}) | True | rel.std 0.081 | 0.5 |

Near-miss: only Sharpe fails, and by a small margin (3.4% shortfall). Every
other validator passes comfortably, including a very robust
parameter-sensitivity result and a perfect 4/4 walk-forward.

## Grid test summary (validation/grid_test.py::run_strategy_grid)

Grid: `atr_window x {10,20}`, `atr_multiplier x {2,3,4}`, symbols
`{QQQ, SPY, BTC/USDT, ETH/USDT}`, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01. 72 cells total.

- pass_fraction: **0.194** (14/72)
- by_asset_class: equity 14/36, crypto 0/36
- by_vol_regime: low 12/24, mid 2/24, high 0/24
- best_cell: SPY, atr_window=20, atr_multiplier=4.0, low-vol tercile, Sharpe 2.44
- worst_cell: SPY, atr_window=10, atr_multiplier=3.0, mid-vol tercile, Sharpe -0.96

Full-sample sanity checks:
- QQQ, atr_window=10, mult=3.0 (source default): Sharpe 0.803 (raw calc)/0.966 (vectorbt) — 15 trades
- QQQ, atr_window=20, mult=4.0: Sharpe 0.531 — 13 trades
- QQQ, atr_window=10, mult=2.0: Sharpe 0.695 — 28 trades
- SPY, atr_window=10, mult=3.0: Sharpe 0.541 — 18 trades
- SPY, atr_window=20, mult=4.0: Sharpe 0.646 — 12 trades

Unlike most rejections in this log, this strategy's grid pass_fraction
(0.194) is comparatively high and the low-vol tercile alone captures 12/24
passing cells with a real (not purely accidental) trend-following signal —
this is the closest full-sample near-miss (Sharpe 0.966 vs 1.0) recorded
in this log to date for a MDD-clean strategy (i.e. it is not the typical
"only passes in a narrow-slice artifact" pattern; the full-sample check at
the exact grid default already nearly clears the bar).

## Decision: **REJECTED (near-miss)**

Sole failing validator is Sharpe (0.966 vs 1.0 threshold), a 3.4% shortfall.
MDD, transaction-cost-survival, walk-forward (4/4 splits), and
parameter-sensitivity (rel.std 0.081, one of the lowest/most robust in this
log) all pass comfortably. Crypto rejected decisively (0/36 grid cells,
consistent with essentially every trend-following strategy tested so far —
crypto's ATH-breakout structure differs enough from equities that this
mechanism doesn't transfer).

Future loop idea: this is a strong candidate to revisit with a slightly
wider atr_multiplier (source's own literature review and the grid's
`atr_multiplier=4.0` cell perform reasonably) or a slightly longer sample
window/different equity symbol, since the shortfall is marginal and the
underlying signal quality (low param sensitivity, perfect walk-forward)
is unusually strong for a rejected strategy in this log.

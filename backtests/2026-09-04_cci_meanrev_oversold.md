# CCI Oversold Mean-Reversion — Backtest Report (2026-09-04-024)

**Hypothesis:** Per QuantifiedStrategies.com (https://www.quantifiedstrategies.com/cci-trading-strategy/),
a short-lookback CCI (9-day, best suited to daily stock/ETF data) that
crosses below an oversold threshold (source uses -90) signals a
short-term mean-reversion opportunity: long when CCI crosses into
oversold territory, exit when price exceeds the pre-entry rolling high
(source's "price exceeds prior high" rule) or after `max_hold_days`.
Source's own SPY backtest reported profit factor ~1.8, max drawdown ~23%.

## Primary config (QQQ, cci_window=9, oversold_threshold=-90.0, exit_lookback=20, max_hold_days=15)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | **False** | 0.591 | 1.0 |
| max_drawdown | **False** | 0.313 | 0.25 |
| transaction_cost_survival (10bps, 73 trades) | True | 0.523 | 0.5 |
| walk_forward (manual 4-split fallback; vectorbt splitter still broken) | True | 0.75 (3/4 splits positive) | 0.75 |
| parameter_sensitivity (cci_window in {9,14,20}, oversold=-90) | **False** | rel.std 0.523 | 0.5 |

## Grid test summary (validation/grid_test.py::run_strategy_grid)

Grid: `cci_window x {9,14,20}`, `oversold_threshold x {-90,-120}`, symbols
`{QQQ, SPY, BTC/USDT, ETH/USDT}`, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01. 72 cells total.

- pass_fraction: **0.125** (9/72)
- by_asset_class: equity 9/36, crypto 0/36
- by_vol_regime: low 9/24, mid 0/24, high 0/24
- best_cell: SPY, cci_window=9, oversold_threshold=-120, low-vol tercile, Sharpe 2.42 (narrow-slice artifact)
- worst_cell: QQQ, cci_window=14, oversold_threshold=-120, mid-vol tercile, Sharpe -0.28

Full-sample sanity check at grid-best-ish configs:
- QQQ, cci_window=9, threshold=-90: Sharpe 0.491 (73 trades)
- QQQ, cci_window=9, threshold=-120: Sharpe 0.171 (62 trades)
- SPY, cci_window=9, threshold=-90: Sharpe 0.303 (71 trades)
- SPY, cci_window=9, threshold=-120: Sharpe 0.308 (61 trades)

Same pattern as most rejected strategies in this log: the best grid cell
(low-vol tercile, narrow slice) is far stronger than the same config's
full-sample Sharpe, confirming it's a slice artifact rather than a stable
edge.

## Decision: **REJECTED**

Sharpe fails on the primary config (0.591 vs 1.0 threshold) and max
drawdown also fails (31.3% vs 25% ceiling) — a rare case where the
strategy fails on the drawdown side rather than pure Sharpe, likely
because CCI-oversold entries during sustained downtrends (2022) get
repeatedly stopped into further drawdown before the "price recovers above
prior high" exit triggers, unlike bounded-hold mean-reversion designs
(e.g. RSI2-meanrev, BB-meanrev) which usually cap losses faster.
Parameter sensitivity also fails (marginal, rel.std 0.523 vs 0.5 ceiling)
— Sharpe drops meaningfully as cci_window widens from 9 to 20. Crypto
rejected decisively (0/36 grid cells). Only transaction-cost-survival and
the manual walk-forward fallback passed.

Future loop idea: try a tighter stop-loss or a shorter max_hold_days to
cap the drawdown tail, or exit on CCI crossing back above a mid-band
(e.g. 0 or +100) rather than waiting for price to exceed the pre-entry
rolling high, which can be a very distant target during a strong
downtrend.

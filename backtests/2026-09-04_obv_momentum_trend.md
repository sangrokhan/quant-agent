# OBV-Momentum Trend Confirmation — Backtest Report (2026-09-04-027)

**Hypothesis:** Per TradingCompendium's OBV guide
(https://tradingcompendium.com/en/technical-indicators/obv-on-balance-volume):
OBV is best used as a volume-based CONFIRMATION filter, not a standalone
signal; the source's only concrete numeric variant is applying a moving
average to the OBV line and trading crossovers of OBV vs its own EMA.
Operationalized here as: long when close > SMA(200) (coarse uptrend
filter) AND OBV crosses above its own EMA(obv_ema_window) (volume-momentum
confirmation); exit when either condition breaks.

## Primary config (QQQ, obv_ema_window=20, trend_window=200)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | **True** | 1.243 | 1.0 |
| max_drawdown | True | 0.179 | 0.25 |
| transaction_cost_survival (10bps, 108 trades) | True | 1.050 | 0.5 |
| walk_forward (manual 4-split fallback; vectorbt splitter still broken) | True | 0.75 (3/4 splits positive) | 0.75 |
| parameter_sensitivity (obv_ema_window in {10,20,30}) | True | rel.std 0.037 | 0.5 |

All 5 standard validators pass on QQQ. Walk-forward split 1 (roughly
2020-2021 COVID-recovery/meme-stock era) is the sole negative split
(Sharpe -0.797) but the other 3 splits are strongly positive, clearing
the 0.75 pass-fraction threshold.

## SPY check (same config) — near-miss

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | **False** | 0.967 | 1.0 |
| max_drawdown | True | 0.124 | 0.25 |

SPY is a very close near-miss (3.3% shortfall) — same pattern as several
other strategies in this log that pass on QQQ but narrowly miss on SPY,
suggesting QQQ's stronger/more persistent tech-sector trends this sample
period favor trend+volume-confirmation constructions somewhat more than
the broader S&P 500.

## Grid test summary (validation/grid_test.py::run_strategy_grid)

Grid: `obv_ema_window x {10,20,30}`, `trend_window x {100,200}`, symbols
`{QQQ, SPY, BTC/USDT, ETH/USDT}`, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01. 72 cells total.

- pass_fraction: **0.25** (18/72)
- by_asset_class: equity 18/36, crypto 0/36
- by_vol_regime: low 12/24, mid 6/24, high 0/24 — notably broader than
  most strategies in this log (mid-vol contributes a real 6/24, not just
  1-2 residual cells)
- best_cell: QQQ, obv_ema_window=30, trend_window=100, low-vol tercile, Sharpe 2.78
- worst_cell: QQQ, obv_ema_window=30, trend_window=100, high-vol tercile, Sharpe -0.65

Full-sample sanity checks (obv_ema_window x trend_window=200, Sharpe/trades):
- QQQ: ow=10 → 0.944/155, ow=20 → 1.033/108, ow=30 → 0.989/90
- SPY: ow=10 → 0.741/165, ow=20 → 0.803/119, ow=30 → 0.833/101

All QQQ trend_window=200 configs are near or above the 1.0 raw-Sharpe bar
(vectorbt's Sharpe calc gives 1.243 at the primary config, higher than
the simple mean/std approximation of 1.033) — a genuinely stable pattern
across the obv_ema_window sweep, not a single lucky cell.

## Decision: **ACCEPTED (QQQ only)**

QQQ clears all 5 standard validators. SPY is a near-miss (Sharpe 0.967)
and is NOT covered by this acceptance — do not extend to SPY without
further validation. Crypto rejected decisively (0/36 grid cells) —
OBV's cumulative-volume construction may behave differently on 24/7
markets with less clearly delineated "session" volume, or simply lacks
the same trend/volume co-movement structure BTC/ETH exhibit in this
sample.

# Hull Moving Average (HMA) Crossover Trend — Backtest Report (2026-09-04-026)

**Hypothesis:** Per CoinQuant's BTC/USDT HMA strategy page
(https://www.coinquant.ai/strategies/btc-hma-5m-backtest): a single HMA
crossed by price signals a momentum shift -- long when close crosses
above HMA(hma_window), exit on cross below. Source's own 5-minute BTC
backtest was decisively negative (ROI -99.91%, Sharpe -8.21) due to
whipsaw at high frequency; this iteration tests the same rule at daily
bar frequency on equity and crypto instead.

## Primary config (SPY, hma_window=40 — best full-sample config found)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | **False** | 0.906 | 1.0 |
| max_drawdown | True | 0.180 | 0.25 |
| transaction_cost_survival (10bps, 154 trades) | True | 0.621 | 0.5 |
| parameter_sensitivity (hma_window in {10,20,40}) | True | rel.std 0.287 | 0.5 |
| walk_forward | skipped | -- | -- (Sharpe already fails decisively enough not to warrant it, per Step 7 guidance) |

## Grid test summary (validation/grid_test.py::run_strategy_grid)

Grid: `hma_window x {10,20,40}`, symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01. 36 cells total.

- pass_fraction: **0.25** (9/36)
- by_asset_class: equity 9/18, crypto 0/18
- by_vol_regime: low 6/12, mid 2/12, high 1/12
- best_cell: QQQ, hma_window=10, low-vol tercile, Sharpe 2.59 (narrow-slice artifact)
- worst_cell: BTC/USDT, hma_window=10, low-vol tercile, Sharpe -0.22

Full-sample sanity checks (Sharpe, num entries):
- QQQ hma_window=10: 0.354 (315 trades) — extreme turnover, whipsaw as source itself warns
- QQQ hma_window=20: 0.501 (223 trades)
- QQQ hma_window=40: 0.629 (151 trades)
- SPY hma_window=10: 0.356 (322 trades)
- SPY hma_window=20: 0.623 (210 trades)
- SPY hma_window=40: 0.753 (154 trades) — best raw calc; vectorbt Sharpe 0.906

Turnover falls sharply as hma_window widens (10→40 roughly halves-then-halves
trade count again) and Sharpe rises correspondingly, consistent with the
source's own documented whipsaw problem at short/high-frequency windows —
even the best full-sample window (40) remains a near-miss rather than a pass.

## Decision: **REJECTED (near-miss)**

Sole failing validator at the best full-sample config (SPY, hma_window=40)
is Sharpe (0.906 vs 1.0, a 9.4% shortfall) — MDD, transaction-cost
survival, and parameter sensitivity all pass. Crypto rejected decisively
(0/18 grid cells), consistent with the source's own finding that this
simple single-line crossover whipsaws badly without a trend/volatility
filter. Every hma_window tested on QQQ/SPY individually falls short of 1.0
Sharpe at full sample, though the trend toward better performance at wider
windows (fewer, cleaner crossovers) is clear and monotonic across all 3
values tested.

Future loop idea: this is a second consecutive near-miss trend-following
strategy (after 2026-09-04-025's chandelier ATH breakout) — a combined
approach (e.g. HMA crossover gated by the low-vol-regime filter already
validated and accepted in 2026-09-03-021, or an even wider hma_window like
60-80) could plausibly close the remaining Sharpe gap by filtering out the
choppy-regime whipsaw the source itself identifies as the strategy's core
weakness.

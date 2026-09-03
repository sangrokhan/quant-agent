# Stochastic Oversold Crossover — Backtest Report (2026-09-04-028)

**Hypothesis:** Per QuantifiedStrategies.com's stochastic indicator article
(https://www.quantifiedstrategies.com/stochastic-indicator-strategy/):
%K crosses above %D while BELOW an oversold threshold (source uses 20)
signals a short-term mean-reversion buy. Source's own SPY backtest
(1993-present, 556 trades) reports profit factor 2.2, MDD 19.8%. Source
explicitly notes a PURE %K/%D crossover (without the zone gate) performed
worse in their own testing.

## Primary config (QQQ, k_window=9, d_window=3, oversold_threshold=20.0, max_hold_days=10)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | **False** | 0.902 | 1.0 |
| max_drawdown | True | 0.060 | 0.25 |
| transaction_cost_survival (10bps, 31 trades) | True | 0.820 | 0.5 |
| parameter_sensitivity (k_window x oversold_threshold, 4 combos) | True | rel.std 0.153 | 0.5 |
| walk_forward | skipped (Sharpe already fails decisively enough not to warrant it) | -- | -- |

## Grid test summary (validation/grid_test.py::run_strategy_grid)

Grid: `k_window x {9,14}`, `oversold_threshold x {20,25}`, symbols
`{QQQ, SPY, BTC/USDT, ETH/USDT}`, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01. 48 cells total.

- pass_fraction: **0.25** (12/48)
- by_asset_class: equity 12/24, crypto 0/24
- by_vol_regime: low 6/16, mid 0/16, high 6/16 -- unusual: unlike almost
  every other strategy in this log (which are 0% in high-vol), this one
  splits its passing cells evenly between low AND high vol, 0% in mid --
  plausibly because oversold-bounce entries need SOME volatility to
  generate a meaningful %K/%D range swing at all, similar to the RSI
  divergence finding (2026-09-03-019).
- best_cell: QQQ, k_window=9, oversold_threshold=25, low-vol tercile, Sharpe 2.07
- worst_cell: QQQ, k_window=14, oversold_threshold=20, mid-vol tercile, Sharpe -1.22

Full-sample sanity checks (Sharpe, trades):
- QQQ: (9,20)→0.75/31, (9,25)→0.665/47, (14,20)→0.694/39, (14,25)→0.486/45
- SPY: (9,20)→0.738/30, (9,25)→0.461/40, (14,20)→0.683/30, (14,25)→0.297/42

Best full-sample raw config is k_window=9/oversold_threshold=20 on both
QQQ and SPY (~0.74-0.75 raw calc, 0.902 vectorbt-Sharpe on QQQ) -- looser
threshold (25) or longer lookback (14) both degrade Sharpe.

## Decision: **REJECTED (near-miss)**

Sole failing validator at the primary QQQ config is Sharpe (0.902 vs
1.0, a 9.8% shortfall). MDD is exceptionally clean (6.0%, one of the
tightest in this log), transaction-cost survival and parameter
sensitivity both pass comfortably. Crypto rejected decisively (0/24 grid
cells). The unusual low+high (not low-only) vol-regime pass pattern is
worth noting for future work.

Future loop idea: the tight MDD (6%) suggests low position-sizing/holding
risk -- a future loop could try loosening max_hold_days or combining with
a volatility filter (given the low+high vol-regime split found here) to
try to close the remaining ~10% Sharpe gap.

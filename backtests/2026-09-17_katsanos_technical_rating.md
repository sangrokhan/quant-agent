# Backtest report: Katsanos Technical Rating Composite (TASC Jun 2018)

**Hypothesis**: A 5-factor weighted composite score (VFI money-flow sign,
close-above-100SMA, rising-100SMA, price-persistence-above-trend
"Stiffness", and a broad-market-trend confirmation condition, double-
weighted) identifies high-conviction long entries, analogous to an
analyst-style stock rating system.

**Source**: https://traders.com/Documentation/FEEDbk_docs/2018/06/TradersTips.html
(TradeStation section, read via browser_exec)

## Grid test (Step 6)
- param_grid: condition_sum_entry=[4,5,6] (of max 6), max_hold_days=[10,20,40]
- symbols: equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT]
- vol_regime_splits=3
- total_cells=108, passed_cells=26, pass_fraction=0.241
- by_asset_class: equity 22/54 (0.407), crypto 4/54 (0.074)
- by_vol_regime: low 20/36 (0.556), mid 6/36 (0.167), high 0/36
- best_cell: equity SPY low-vol, condition_sum_entry=5/max_hold_days=10, Sharpe 2.72

## Full-sample Sharpe sweep (all symbols x 9 configs)
| Symbol | best config | Sharpe | MDD |
|---|---|---|---|
| QQQ | condition_sum_entry=4, max_hold_days=40 | 1.161 | 0.276 (FAILS MDD 0.25 threshold) |
| SPY | condition_sum_entry=4, max_hold_days=40 | 1.074 | 0.198 (PASSES) |
| BTC/USDT | condition_sum_entry=5, max_hold_days=20 | 0.231 | (all fail Sharpe) |
| ETH/USDT | condition_sum_entry=5, max_hold_days=10 | 0.243 | (all fail Sharpe) |

QQQ's best-Sharpe config fails on max_drawdown (0.276 > 0.25) despite
clearing the Sharpe bar -- not accepted.

## Single-config validators (Step 7) -- SPY, condition_sum_entry=4, max_hold_days=40
| Validator | Result | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | PASS | 1.074 | 1.0 |
| max_drawdown | PASS | 0.198 | 0.25 |
| transaction_cost_survival (10bps/trade, 43 trades) | PASS (thin) | 1.007 | 0.5 |
| walk_forward (4 manual date-slices; vbt.utils.splitting still broken, known workaround) | PASS | 4/4 | 0.75 |
| parameter_sensitivity (9-config sweep) | PASS | 0.311 | 0.5 |

All 5 validators pass for SPY.

## Decision: ACCEPTED (SPY only)
QQQ rejected: best config clears Sharpe (1.161) but fails max_drawdown
(0.276 vs 0.25 threshold) -- a near-miss on a different validator than
usual. Crypto (BTC/USDT, ETH/USDT) rejected decisively -- Sharpe never
exceeds 0.25 on any config, severe drawdowns (0.45-0.62).

**Known limitation flagged**: this strategy's Cond5 (source's own
"MarketTrendSymbol" condition, default SPY) is approximated using the
SAME symbol's own longer-horizon trend rather than a true external
market-benchmark fetch, since this repo's generate_signals/generate_returns
contract only receives a single price_df. For SPY itself this is exactly
correct (self-referential); for QQQ and crypto it's a proxy, not the
source's literal design -- a future loop with a multi-symbol-aware
strategy contract could implement Cond5 more faithfully and might change
QQQ's outcome.

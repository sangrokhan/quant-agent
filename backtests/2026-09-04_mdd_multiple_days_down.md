# Backtest Report: Larry Connors Multiple Days Down (MDD) Mean-Reversion

**Strategy file:** `strategies/2026-09-04_mdd_multiple_days_down.py`
**Date:** 2026-09-04
**Source:** https://www.quantifiedstrategies.com/multiple-days-up-and-multiple-days-down-trading-strategy/
(retrieved via browser_exec after web_search DDGS/Yahoo TLS failure)

## Hypothesis

Buy an ETF at close when close > SMA200 (uptrend) AND close < SMA5 (below
short-term mean) AND price has fallen on 4 of the last 5 trading days;
exit at close when price closes back above SMA5. No stop-loss (per source).

## Grid test summary (down_days_required x down_window x 4 symbols x 3 vol terciles = 48 cells)

- pass_fraction: **35.4%** (17/48)
- by_asset_class: equity 15/24 (63%), crypto 2/24 (8%)
- by_vol_regime: low 8/16, mid 5/16, high 4/16
- best_cell: SPY, down_days_required=4/down_window=4, mid-vol regime, Sharpe 1.83

## Full-sample single-config metrics (canonical Connors config: down_window=5, down_days_required=4)

| Symbol   | Sharpe | Pass | MDD   | Pass | TC-adj Sharpe (10bps, entry+exit) | Pass |
|----------|--------|------|-------|------|-------------------------------------|------|
| SPY      | 1.170  | Yes  | 0.081 | Yes  | 0.085                               | No   |
| QQQ      | 0.658  | No   | 0.055 | Yes  | (not run, Sharpe already fails)     | -    |
| BTC/USDT | 0.511  | No   | 0.240 | Yes  | (not run, Sharpe already fails)     | -    |
| ETH/USDT | 0.479  | No   | 0.484 | No   | (not run, Sharpe already fails)     | -    |

Parameter sensitivity (SPY Sharpe across 4 down_window/down_days_required
combos, relative std): 0.157 (well under 0.5 threshold).

## Decision: REJECTED (all symbols)

- **SPY** clears gross Sharpe (1.17) and MDD (8.1%) at the canonical config,
  with reasonably stable parameter sensitivity (relstd 0.16), but
  **decisively fails transaction-cost survival** (net Sharpe 0.09 vs 0.5) --
  153 trades/7.7yr with a thin average per-trade edge cannot absorb even a
  modest 10bps/leg cost assumption. This is the SECOND strategy tested this
  run (after the FVG retracement strategy, 2026-09-04-095) to clear gross
  Sharpe/MDD cleanly but fail on trade-cost drag alone -- suggests many
  short-holding-period equity mean-reversion setups in this
  parameter/threshold range share the same "thin edge, moderate frequency"
  cost-fragility profile.
- **QQQ, BTC/USDT, ETH/USDT** all fail gross Sharpe outright (0.66, 0.51,
  0.48 respectively).

Future idea: this is the third consecutive strategy this cron trigger
(after FVG-095 and, more loosely, dual-momentum-097's MDD near-miss) to
fail specifically on the transaction-cost gate rather than raw signal
quality -- a future loop iteration could usefully investigate whether
`check_transaction_cost_survival`'s flat 10bps/round-trip assumption is
unrealistically punitive for these setups, or whether it's correctly
identifying a real class of strategies (short-hold mean-reversion with
thin per-trade edge) that don't survive realistic costs.

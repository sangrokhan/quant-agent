# Backtest Report: Larry Connors' %b (Bollinger Percent-B) 3-day persistence mean-reversion

**Strategy file:** `strategies/2026-09-06_connors_pctb_3day_persist.py`
**Date:** 2026-09-06

## Hypothesis

Buy when close > 200d SMA AND %b < 0.2 for 3 consecutive closing days
(5-day Bollinger window, 2 std devs); exit when %b closes above 0.8. Per
https://www.quantifiedstrategies.com/larry-connors-b-strategy/ (Larry
Connors, *High Probability Trading* Ch. 5).

## Grid test (Step 6)

`param_grid`: bb_window in {5,10}, persistence_days in {2,3},
exit_threshold in {0.7,0.8}; symbols equity=[QQQ,SPY],
crypto=[BTC/USDT,ETH/USDT]; vol_regime_splits=3. 96 total cells.

- pass_fraction: 0.1146 (11/96)
- by_asset_class: equity 11/48, crypto 0/48
- by_vol_regime: low 10/32, mid 0/32, high 1/32
- best_cell (tercile-level, not full-sample): bb_window=5,
  persistence_days=2, exit_threshold=0.7, QQQ, low-vol, Sharpe 1.995

## Full-sample manual scan (Step 6/7)

Expanded scan over bb_window in {5,8,10,15}, persistence_days in {2,3,4},
exit_threshold in {0.7,0.8} on full-sample QQQ/SPY (2019-2026), filtered
to configs with >=5 trades to avoid statistically meaningless single-digit
sample artifacts. **Best full-sample Sharpe found was only 0.76** (SPY,
bb_window=5, persistence_days=2, exit_threshold=0.8, 31 trades) — well
below the 1.0 threshold. Most configs with tighter persistence
requirements (persistence_days=3-4) generated too few trades (7-16) to be
statistically meaningful even when nominally passing Sharpe.

Consistent with the already-rejected simpler %b variant (2026-09-04-107,
full-sample Sharpe 0.59) — this repo's 2019-2026 sample period does not
show a robust edge from Bollinger %b mean-reversion regardless of the
specific band window or persistence-day requirement tried, both with and
without the multi-day persistence filter.

## Decision: **REJECT**

Full-sample Sharpe fails threshold (best 0.76 < 1.0) on every
statistically-meaningful (>=5 trades) config across the grid and the
expanded manual scan. Skipped single-config validator suite (MDD/tx-cost/
walk-forward/param-sensitivity) given the decisive full-sample Sharpe
failure across the whole parameter space — no config clears the primary
gate to warrant deeper validation (workload judgment call under `max`,
prioritizing exploring a new candidate next iteration over exhaustively
validating an already-clear-miss family).

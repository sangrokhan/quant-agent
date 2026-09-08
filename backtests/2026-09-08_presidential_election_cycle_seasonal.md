# Backtest Report: Presidential Election Cycle Seasonality (2026-09-08)

## Hypothesis
US equities historically outperform in years 3-4 (pre-election + election
year) of the 4-year presidential cycle vs years 1-2 (post-election +
midterm), per Yale Hirsch's Stock Trader's Almanac, summarized at
https://www.quantifiedstrategies.com/president-election-cycles/ (visited
2026-09-08 via browser_exec, after web_search again failed with the same
DuckDuckGo/Yahoo TLS error observed in iteration 1 this trigger).

## Strategy file
`strategies/2026-09-08_presidential_election_cycle_seasonal.py`

## Grid test summary (Step 6)
Grid: `long_cycle_years` in [(3,4),(3,),(4,)] x `trend_window` in [0,100],
equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT), vol_regime_splits=3. 72
total cells.

- pass_fraction: 0.264 (19/72)
- by_asset_class: equity 19/36 passed, crypto 0/36 (decisive failure, as
  expected -- this is a US-political-cycle-specific effect)
- by_vol_regime: low 12/24, mid 5/24, high 2/24
- best_cell: long_cycle_years=(3,4), trend_window=0, QQQ, mid-vol, Sharpe=2.05
- worst_cell: long_cycle_years=(3,4), trend_window=100, QQQ, high-vol, Sharpe=-0.49

## Single-config validation (best config: long_cycle_years=(3,4), trend_window=0)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Walk-fwd pass frac | Param sensitivity (rel std) | Num trades |
|---|---|---|---|---|---|---|
| QQQ | 1.278 (pass) | 0.286 (FAIL, thresh 0.25) | 1.276 (pass) | 1.0 (pass) | 0.316 (pass) | 2 |
| SPY | 0.914 (FAIL) | 0.341 (FAIL) | 0.912 (pass) | 1.0 (pass) | 0.332 (pass) | 2 |

Caveat: only 2 position-entry trades over the 2018-2026 (8.5yr) sample --
the underlying calendar cycle only completes ~2 full transitions in this
window, so all validator statistics here have very low sample size/
statistical power compared to indicator-based strategies with dozens of
trades. Walk-forward's 4-way split is a particularly weak signal for a
calendar-only strategy for the same reason.

## Decision: REJECTED

QQQ passes Sharpe/txcost/walk-forward/param-sensitivity but fails max
drawdown (0.286 vs 0.25 threshold) -- the strategy's long exposure spans
multi-year drawdowns (e.g. the 2022 rate-hike bear market falls within a
cycle-year-3/4 window) with no risk management beyond the calendar gate.
SPY additionally fails the Sharpe threshold outright. Given the low trade
count and correspondingly low statistical confidence, this is a weaker
rejection than a typical indicator-based strategy failure, but the MDD
breach persists across both equities tested and reflects a real structural
weakness (unhedged multi-year exposure) rather than parameter fragility.

# Backtest Report: SPY/QQQ Pairs Trading (Regression Hedge Ratio + Spread Z-Score)

**Strategy file:** `strategies/2026-09-04_spy_qqq_pairs_zscore.py`
**Date:** 2026-09-04
**Source:** https://www.quantifiedstrategies.com/correlation-trading-strategies/
(retrieved via browser_exec after web_search DDGS/Yahoo TLS failure)

## Hypothesis

SPY and QQQ are highly correlated (~0.85, 60-day). Estimate a rolling OLS
hedge ratio (beta) of QQQ on SPY, construct the spread, z-score it, and
trade mean-reversion when the z-score exceeds +/-2 std, exiting near 0.

## Full-sample metrics (QQQ as primary, SPY as hedge; hedge_window=z_window=60)

| entry_z | Sharpe | Pass | MDD   | Pass | Trades |
|---------|--------|------|-------|------|--------|
| 1.5     | 0.207  | No   | 0.115 | Yes  | 945    |
| 2.0     | 0.308  | No   | 0.089 | Yes  | 627    |
| 2.5     | 0.433  | No   | 0.076 | Yes  | 291    |

## Robustness check (SPY as primary, QQQ as hedge; multiple hedge/z windows)

| entry_z | hedge_window | Sharpe |
|---------|--------------|--------|
| 2.0 | 30 | -0.297 |
| 2.0 | 60 | -0.047 |
| 2.0 | 90 | -0.619 |
| 2.5 | 30 | -0.708 |
| 2.5 | 60 | -0.188 |
| 2.5 | 90 | -0.285 |
| 3.0 | 30 | -0.746 |
| 3.0 | 60 | 0.400 |
| 3.0 | 90 | -0.540 |

All configurations in both directions (QQQ-vs-SPY and SPY-vs-QQQ) produce
Sharpe far below the 1.0 threshold -- mostly negative when SPY is the
primary/QQQ the hedge, weakly positive but still failing when QQQ is
primary/SPY the hedge.

## Decision: REJECTED

No configuration across 12 tested parameter combinations (3 entry-z values
x 2 primary/hedge directions x up to 3 window sizes) comes close to
clearing the Sharpe threshold; most SPY-primary configs are outright
negative. MDD is fine everywhere (6-26%), confirming the spread-based
approach does manage risk reasonably, but there is no real mean-reverting
edge to harvest between SPY and QQQ at this cost-free level -- the two
indices' spread does not revert reliably enough at any tested lookback/
threshold combination to produce a positive risk-adjusted return, even
before transaction costs are applied. Consistent with the source's own
caveat that "correlation alone is insufficient... test for cointegration
alongside correlation" -- SPY/QQQ's near-identical large-cap tech-heavy
composition likely makes their spread trend rather than mean-revert over
multi-day/week horizons (QQQ has structurally outperformed SPY over most of
the 2019-2026 window), the opposite of what a stationary/cointegrated pair
needs.

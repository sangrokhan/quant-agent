# Backtest Report: Weekly SPY vs XLU Relative-Performance Rotation

**Strategy file:** `strategies/2026-09-23_weekly_spy_xlu_relative_performance_rotation.py`
**KB id:** 2026-09-23-151
**Outcome:** REJECTED (Sharpe + MDD decisive fail)

## Hypothesis + Source

Per QuantifiedStrategies.com's "Weekly Rotating System Between S&P 500 And
Utilities (SPY And XLU)" (read via `browser_exec` Google SERP snippets —
direct article URL 404'd, but the source's snippet was consistent across
multiple independent hits): each week, hold whichever of SPY or XLU had the
better trailing relative performance, always fully invested (never cash).

## Single-config validators (SPY, full sample 2018-01-01 to 2026-09-01)

Grid-best config: `lookback_days=20, rebalance_days=5`

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.725 | 1.0 |
| Max drawdown | **FAIL** | 0.367 | 0.25 |
| Transaction cost survival | pass | 0.638 | 0.5 |
| Walk-forward (4 splits) | pass | 1.0 (4/4) | 0.75 |
| Parameter sensitivity | pass | 0.231 rel-std | 0.5 |

## Grid test summary

36 cells: `lookback_days ∈ {10,20,40}` × `rebalance_days ∈ {5,10}` ×
symbols `{QQQ, SPY}` × 3 vol-regime terciles (equity only — XLU is the
comparison asset itself).

- **pass_fraction:** 0.306 (11/36)
- **By vol regime:** low 8/12 (67%), mid 3/12 (25%), high 0/12 (0%)
- **Best cell:** SPY, low-vol, `lookback_days=20/rebalance_days=5`, Sharpe 1.77
- **Worst cell:** SPY, mid-vol, `lookback_days=10/rebalance_days=10`, Sharpe -0.41

## Decision

**Rejected.** Sharpe and MDD both decisively fail full-sample. Structural
issue: because the strategy is always fully invested (rotates into XLU
rather than cash), it provides no protection during systemic drawdowns
(2020 COVID, 2022 bear) where both SPY and XLU fell together. A future
revisit should add a genuine cash/flat state as a third rotation option.

# Backtest Report: SPY/XLU/Cash Three-Way Rotation (Near-Miss Rescue)

**Strategy file:** `strategies/2026-09-23_spy_xlu_cash_three_way_rotation.py`
**KB id:** 2026-09-23-152
**Outcome:** REJECTED (extreme near-miss)

## Hypothesis

Direct rescue of this cron trigger's own near-decisive rejection
(2026-09-23-151, SPY vs XLU always-invested two-asset rotation, MDD
decisive fail 0.367). Adds a genuine cash/flat state: whenever BOTH
underlying and XLU trailing returns are non-positive (systemic risk-off
proxy), hold cash; otherwise rotate into the stronger of the two.

## Single-config validators (QQQ, full sample 2018-01-01 to 2026-09-01)

Grid-best config: `lookback_days=20, rebalance_days=10`

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL (near-miss)** | 0.929 | 1.0 |
| Max drawdown | **FAIL (near-miss)** | 0.2516 | 0.25 |
| Transaction cost survival | pass | 0.854 | 0.5 |
| Walk-forward (4 splits) | pass | 1.0 (4/4) | 0.75 |
| Parameter sensitivity | pass | 0.368 rel-std | 0.5 |

MDD improved dramatically vs the parent strategy: **0.367 → 0.2516** (a
~31% relative reduction), confirming the cash-state diagnosis was correct.
It's now just **0.0016 over** the 0.25 budget — the closest near-miss
recorded in this trigger.

## Grid test summary

36 cells: `lookback_days ∈ {10,20,40}` × `rebalance_days ∈ {5,10}` ×
symbols `{QQQ, SPY}` × 3 vol-regime terciles.

- **pass_fraction:** 0.278 (10/36)
- **By vol regime:** low 8/12 (67%), mid 2/12 (17%), high 0/12 (0%)
- **Best cell:** QQQ, low-vol, `lookback_days=20/rebalance_days=10`, Sharpe 1.83
- **Worst cell:** SPY, mid-vol, `lookback_days=10/rebalance_days=10`, Sharpe -0.55

## Decision

**Rejected** — but flagged as a genuine, very close near-miss worth a
follow-up retune (e.g. cash triggered when EITHER asset — not both — has
non-positive trailing return, for faster de-risking, or a shorter
lookback window).

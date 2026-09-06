# Backtest Report: Disparity Index Uptrend Mean-Reversion (REJECTED)

**Strategy file:** `strategies/2026-09-06_disparity_index_uptrend_meanrev.py`
**Date:** 2026-09-06
**Source:** https://gocharting.com/docs/charting/technical-indicator/oscillators/disparity-index

## Hypothesis

Per GoCharting's Disparity Index docs: "For mean-reversion: when the
Disparity Index reaches extreme negative values in an uptrend, enter long
as price returns toward its moving average." Gated by an uptrend filter
(50-day SMA rising) and volume confirmation, per the source's own warnings
against fading extremes in a downtrend and to confirm reversions with
volume. First Disparity Index strategy in this repo.

## Step 6 — Grid test summary (108 cells: di_entry_threshold[-3,-5,-8] x
max_hold_days[7,10,15] x 2 asset classes x 2 symbols x 3 vol regimes)

- **Overall pass_fraction: 0.037** (4/108) — decisively weak
- **By asset class:** equity 4/54 (0.074), crypto 0/54 (decisive reject)
- **By vol regime:** low 0/36, mid 4/36 (0.111), high 0/36
- **Best cell:** di_entry_threshold=-5.0, max_hold_days=10, QQQ, mid-vol,
  Sharpe=1.86 (isolated cherry-pick)

## Step 7 — Single-config validation (best cell config, QQQ, full sample
2019-01-01 to 2026-09-01)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **False** | 0.299 | >= 1.0 |
| Max drawdown | True | 0.113 | <= 0.25 |
| TC survival (10bps/trade, 12 trades) | **False** | net Sharpe 0.272 | >= 0.5 |

Full-sample Sharpe far below threshold; only 12 trades over 7.7yr so the
one good mid-vol grid cell was noise from a narrow-slice cherry-pick, not a
real edge. Skipped walk-forward/parameter sensitivity given the decisive
full-sample rejection.

## Outcome: **REJECTED**

Decisive rejection across the grid (0.037 pass_fraction) and full-sample
Sharpe/TC-survival both fail on the best config. The volume-confirmation +
uptrend-gate filters used here were likely too restrictive, leaving too few
trades (12) for a real statistical edge to emerge. Keeping the file as a
rejected-attempt record.

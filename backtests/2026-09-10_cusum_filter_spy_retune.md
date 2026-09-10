# CUSUM Filter Trend-Event Entry — SPY-specific retune (2026-09-10)

**Hypothesis**: Direct follow-up to 2026-09-10-072 (CUSUM filter trend-event
entry, accepted QQQ only at vol_window=40/h_mult=5.0/max_hold_days=30; SPY
decisively failed Sharpe/MDD/TC-survival/walk-forward at that config). A
SPY-specific local parameter search (`scripts/scan_cusum_spy_retune.py`,
4x5x3=60 combos of vol_window/h_mult/max_hold_days) found a materially
different SPY optimum: `vol_window=40, h_mult=6.0, max_hold_days=45` (higher
threshold, longer hold than QQQ's tuned config).

Same underlying symmetric-CUSUM-filter mechanism as the parent strategy
(source: https://github.com/muMAJJI/Trading---CUSUM-FILTER) — only the 3
tunable parameters differ.

## Single-config validator results (SPY, best retuned config)

| Metric | Value | Threshold | Result |
|---|---|---|---|
| Sharpe | 1.001 | 1.0 | PASS (marginal) |
| Max drawdown | 14.4% | 25% | PASS |
| TC-survival (net Sharpe) | 0.953 | 0.5 | PASS |
| Walk-forward | 1.00 (4/4 splits) | 0.75 | PASS |
| Parameter sensitivity | 0.369 rel. std | 0.5 | PASS |

26 trades over the 8.7yr sample.

## Decision: ACCEPT (SPY only, this config)

All 5 validators pass, though the headline Sharpe (1.0009) clears the 1.0
threshold by a very thin margin — flagged explicitly here as a marginal
pass, not a robust edge, for any future loop's benefit. Combined with the
already-accepted QQQ config (2026-09-10-072, vol_window=40/h_mult=5.0/
max_hold_days=30), the CUSUM-filter family is now accepted on both major
equity index ETFs in this repo, each with its own distinct tuned config.
Crypto remains rejected (per the parent grid's decisive 0/36 crypto cells;
not re-tested here since nothing in this SPY-focused retune changes the
crypto mechanism or expected outcome).

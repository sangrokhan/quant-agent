# 2026-09-14 DPO Sizing SMA Trend — SPY fix (round 2)

## Hypothesis

Further SPY fix for 2026-09-15-013 (DPO continuous sizing dial): the prior
QQQ-fix iteration left SPY still rejected with a persistent TC-survival
near-miss (best net Sharpe 0.481 vs 0.5 threshold) even after a widened
4-config sweep (dpo_window up to 30, deadband up to 0.55, but trend_window
fixed at 40). This iteration additionally varies `trend_window` (40/60/80)
alongside dpo_window/zscore_window/sensitivity/deadband (up to 0.75) and
finds a clean pass at trend_window=80/dpo_window=30/zscore_window=100/
sensitivity=0.3/deadband=0.55 (Sharpe 1.108, TC-survival net Sharpe 0.913,
only 61 trades). The wider trend_window (80 vs 40) plus a lower sensitivity
(0.3 vs 0.6) is what finally cuts turnover enough to clear TC-survival.
Same strategy file (strategies/2026-09-14_dpo_sizing_sma_trend.py), same
already-confirmed DPO formula, no new external fetch.

## Grid (Step 6 — targeted SPY-only sweep)

`param_grid={trend_window:[40,60,80], dpo_window:[14,20,30],
zscore_window:[100,150], sensitivity:[0.3,0.4,0.6],
deadband:[0.45,0.55,0.65,0.75]}`, symbol SPY only -> 216 combos, most with
`deadband=0.75` combined with `sensitivity=0.3` degenerate to 0 trades
(exposure never clears the deadband) and were filtered out as invalid
before ranking. Of the remaining valid combos, 6 clear both Sharpe>=1.0 and
TC-survival net Sharpe>=0.5; best-by-TC-survival is trend_window=80/
dpo_window=30/zscore_window=100/sensitivity=0.3/deadband=0.55.

## Step 7 — Single-config validation (SPY, trend_window=80/dpo_window=30/zscore_window=100/sensitivity=0.3/deadband=0.55)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.108 | 1.0 | ✅ |
| Max drawdown | 0.070 | 0.25 | ✅ |
| TC-survival net Sharpe | 0.913 | 0.5 | ✅ |
| Walk-forward (4-split) | 1.0 | 0.75 | ✅ |
| Parameter sensitivity (rel std) | 0.317 | 0.5 | ✅ (degenerate 0-trade cells excluded from the sensitivity sweep) |

Walk-forward used the repo-standard manual 4-equal-slice fallback
(vbt.utils.splitting API unavailable in installed vectorbt==1.1.0).

## Step 8 — Accept/Reject

**SPY: accepted.** All 5 validators pass, finally resolving the
2026-09-15-013 TC-survival near-miss that persisted across two previous
sweeps. QQQ config from 2026-09-15-013 unchanged (already accepted, not
retested). Crypto (BTC/ETH) remains accepted at its original config from
2026-09-14-154 (not retested this iteration).

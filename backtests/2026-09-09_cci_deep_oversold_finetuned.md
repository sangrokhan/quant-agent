# CCI Deep-Oversold Recovery ("-125 hook") — Fine-Tuned Near-Miss Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_cci_deep_oversold_uptrend_recovery.py`
**Knowledge base id:** 2026-09-09-057

## Hypothesis

Direct follow-up to this same cron trigger's earlier rejection
2026-09-09-053 (CCI -200 deep-oversold recovery + 200d SMA uptrend gate,
best SPY Sharpe only 0.917, QQQ 0.658 at same config). A finer parameter
sweep (cci_window in {8..25}, oversold_threshold in {-125..-250},
max_hold_days in {10..40}, 288 combos) found a materially better joint
optimum at cci_window=8, oversold_threshold=-125, max_hold_days=15:
QQQ Sharpe 0.995 (0.005 short of 1.0 -- essentially a coin-flip miss),
SPY Sharpe 1.040 (clears threshold).

## Step 7 single-config validation (cci_window=8, oversold_threshold=-125, max_hold_days=15)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 0.9946 | 1.0395 | >= 1.0 | QQQ near-miss (0.0054 short); SPY pass |
| Max drawdown | 0.101 | 0.130 | <= 0.25 | Yes (both) |
| Net Sharpe after costs (10bps/trade, 47/45 trades) | 0.907 | 0.895 | >= 0.5 | Yes (both) |

## Step 6 grid test summary (single-cell, this config only)

12 cells (QQQ/SPY/BTC/ETH x low/mid/high vol terciles): pass_fraction
0.333 (4/12). Equity 4/6 pass (spread across low and high vol regimes,
not concentrated in one), crypto 0/6 decisive.

## Decision: **REJECTED (extremely narrow near-miss)**

QQQ's Sharpe of 0.9946 is within half a percent of the 1.0 threshold --
essentially at the edge of statistical noise for a 47-trade sample over
7 years. SPY passes cleanly at 1.040. All other validators (MDD,
TC-survival) pass comfortably for both symbols. This is flagged as a
strong near-miss candidate for a future loop to revisit with either a
slightly larger equity universe (to average out single-symbol noise) or
a walk-forward-based config selection rather than full-sample
optimization (which risks overfitting to this exact historical window
given how close the fit is).

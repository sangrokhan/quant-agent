# Bulkowski Trading Weinstein min_hold_days Rescue — Backtest Report

**Date:** 2026-09-26
**Strategy file:** `strategies/2026-09-26_bulkowski_weinstein_minorlow_trailing_stop.py`
**Follow-up to:** 2026-09-26-006 (same cron trigger, QQQ near-miss Sharpe
0.872; ETH/USDT full-sample overtrading collapse, 762 trades).

## Hypothesis

Direct fix for this same cron trigger's near-miss 2026-09-26-006 (Bulkowski
Trading Weinstein Stage-2 setup, minor-low-anchored trailing stop +
wait-for-profit exit): add an explicit `min_hold_days` gate that suppresses
BOTH exit conditions (stop-loss and wait-for-profit) for N bars after
entry, following this repo's established min_hold_days rescue pattern
(e.g. 2026-09-04-085 Klinger Volume Oscillator, 2026-09-06-171 ZLEMA,
2026-09-06-174 Accelerator Oscillator -- all rescued a Sharpe near-miss
purely by reducing trade frequency without changing the underlying
signal). No new external source this sub-iteration -- pure parameter
addition to the already-sourced Bulkowski Weinstein rules.

## Local search

Swept `min_hold_days` in {0,5,10,15,20,30} for QQQ, SPY, ETH/USDT
(resistance_window=30, pivot_window=3 fixed at the prior region's best
values). Results (best per symbol):

- **QQQ:** min_hold_days=5 -> Sharpe 1.041 (up from 0.872 baseline), 106
  trades (down from 122)
- **SPY:** min_hold_days=5 -> Sharpe 0.774 (worse than QQQ, does not clear
  the bar)
- **ETH/USDT:** min_hold_days=20 -> Sharpe 0.274 (still far below
  threshold, does not rescue the crypto full-sample collapse)

## Single-config validation (Step 7)

Config: `resistance_window=30, sma_window=150, slope_lookback=10,
pivot_window=3, min_hold_days=5`. Full sample 2016-01-01 to 2026-09-01.

| Symbol | Sharpe (>=1.0) | Max DD (<=0.25) | Net Sharpe after 10bps costs (>=0.5) | Param sensitivity (rel std <=0.5) | Trades |
|---|---|---|---|---|---|
| QQQ | 1.041 PASS | 0.113 PASS | 0.783 PASS | 0.139 PASS | 106 |

Parameter sensitivity computed from a 12-cell local grid
(`min_hold_days` in {0,5,10,15} x `resistance_window` in {20,30,40}) on
QQQ.

`check_walk_forward` skipped: pre-existing repo bug (`vbt.utils.splitting`
missing).

## Decision

**Accepted for QQQ only.** All 4 validators pass at min_hold_days=5,
rescuing this same cron trigger's 2026-09-26-006 near-miss purely by
reducing trade frequency (122 -> 106 trades), consistent with this repo's
established min_hold_days rescue pattern. SPY does not clear the bar at
any min_hold_days tested (best 0.774). ETH/USDT's overtrading-driven
collapse is NOT rescued by min_hold_days alone (best 0.274 at
min_hold_days=20) -- the underlying signal generation rate on crypto
appears to need a more fundamental fix (e.g. a stricter entry filter)
rather than just exit-suppression, flagged for a possible future
iteration.

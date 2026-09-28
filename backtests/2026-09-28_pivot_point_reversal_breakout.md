# Pivot Point Reversal Breakout — Backtest Report

**Strategy file:** `strategies/2026-09-28_pivot_point_reversal_breakout.py`
**Date:** 2026-09-28

## Hypothesis

Per Bulkowski's Pivot Point Reversal, Downtrend page
(https://thepatternsite.com/PPRD.html, read 2026-09-28 via browser_exec): a
simple 2-bar pattern in a short-term downtrend where today's close exceeds
yesterday's high. Despite the "reversal" name, the source's own data shows
it only reverses the trend 31% of the time in a bull market -- so, matching
this repo's established convention with the similarly-named/rejected-as-
reversal Key Reversal and Hook Reversal patterns, this strategy trades the
disclosed breakout (continuation) direction. Source's own measure rule
(pattern height added to pattern high) hits the target 77% of the time in
bull markets.

## Single-config validators (QQQ, SPY; trend_lookback=3, max_hold_days=30; 2019-01-01..2026-09-01)

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe | 1.260 (pass, thr 1.0) | 0.678 (**fail**, thr 1.0) |
| Max Drawdown | 0.223 (pass, thr 0.25) | 0.211 (pass, thr 0.25) |
| Net Sharpe after costs (10bps/trade) | 1.095 (pass, thr 0.5) | 0.516 (pass, thr 0.5) |
| Walk-forward pass fraction (4 splits) | 1.0 (pass, thr 0.75) | 0.75 (pass, thr 0.75) |
| Parameter sensitivity (relative std, 4-cell sweep) | 0.105 (pass, thr 0.5) | 0.173 (pass, thr 0.5) |

QQQ: **all validators pass.** SPY: only Sharpe fails.

## Step 6 grid summary

Grid: `trend_lookback` in {3, 5} x `max_hold_days` in {20, 30}, QQQ/SPY,
vol_regime_splits=3, 2019-01-01..2026-09-01 (light workload — equity only,
2x2 param grid).

- pass_fraction: 0.583 (14/24) -- strongest grid result of this cron trigger
- by_asset_class: equity 14/24
- by_vol_regime: low 8/8, mid 4/8, high 2/8
- best_cell: trend_lookback=3, max_hold_days=30, QQQ, low-vol regime, Sharpe 2.172
- worst_cell: trend_lookback=5, max_hold_days=30, SPY, mid-vol regime, Sharpe -1.058

Strategy generalizes well across vol regimes on QQQ, holds moderately on
SPY. Unusually high pass_fraction relative to every other small-pattern
strategy tested this trigger (all others 0.0-0.21) -- the "no
open-position constraint" simplicity of this pattern (just close(t) >
high(t-1), vs the extra open/close/isolation constraints of Key/Hook/One-
Day-Reversal) appears to produce a MORE frequent and MORE robust signal on
QQQ/SPY daily bars than the more elaborate small-pattern variants.

## Decision: ACCEPT for QQQ only

QQQ clears all 5 validators. SPY fails only the Sharpe threshold (0.678 <
1.0) -- reject for SPY, but note SPY's other 4 validators (including
TC-survival and walk-forward) do pass, a genuine near-miss rather than a
decisive failure.

# Anchored VWAP Reclaim — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_anchored_vwap_reclaim.py`
**Outcome:** REJECTED (decisive full-sample Sharpe fail)

## Hypothesis

Per daytradingtoolkit.com's "Anchored VWAP Trend Strategy for Day
Traders" (Brian Shannon's anchored-VWAP concept): anchoring a VWAP
calculation to a genuinely significant pivot (confirmed breakout, swing
high/low) rather than resetting daily produces a multi-day/week
volume-weighted average acting as dynamic support/resistance. Source's
exact setup: entry = price returns to touch the anchored VWAP on
declining volume, confirmed by a close back above it on rising volume
within a few bars; stop = beyond the anchored VWAP; target = prior swing
high since the anchor.

Operationalized on daily bars: anchor re-sets on each new
`anchor_window`-day high (breakout proxy); anchored VWAP = cumulative
volume-weighted typical price since that anchor; entry on a below-average-
volume touch of the anchored VWAP followed within `confirm_window` bars
by an above-average-volume close back above it; exit on stop (anchored
VWAP value at entry), target (anchor-window rolling high), or
max_hold_days.

First Anchored VWAP (event-anchored cumulative VWAP as dynamic S/R)
strategy in this repo (0 prior hits) — distinct from Session VWAP
(resets daily) and Volume Profile POC/VAH (rolling-window histogram, not
a cumulative running average from a single anchor event).

## Grid summary (anchor_window=[40,60] x touch_tolerance=[0.01,0.02] x
max_hold_days=[30], equity=[QQQ,SPY] x crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 48, passed_cells: 7, pass_fraction: 0.146
- by_asset_class: equity 7/24 (0.292), crypto 0/24 (0.0 — decisive fail)
- by_vol_regime: low 4/16 (0.25), mid 3/16 (0.1875), high 0/16 (0.0)
- best_cell: anchor_window=60/touch_tolerance=0.02, QQQ mid-vol regime,
  Sharpe 1.48

## Full-sample validation (best grid config: anchor_window=60,
touch_tolerance=0.02, max_hold_days=30)

| Symbol | Trades | Sharpe | MDD |
|---|---|---|---|
| QQQ | 102 | **-0.025 (FAIL, thr 1.0)** | 23.9% (PASS) |
| SPY | 108 | **0.245 (FAIL, thr 1.0)** | 16.6% (PASS) |

Both symbols fail Sharpe decisively on the full sample — QQQ's
full-sample Sharpe is essentially zero (-0.025), a large gap from the
grid's optimistic mid-vol-slice Sharpe of 1.48. This is the same
regime-slice-overfit pattern seen repeatedly this run (Fibonacci Time
Zone, ATR Channel Breakout): a promising-looking single-regime-slice
Sharpe does not survive full-period validation.

## Verdict: REJECTED

Both equities decisively fail full-sample Sharpe; crypto rejected
decisively in the grid (0/24). No further validators (MDD/TC/WF/param
sensitivity) run given the decisive Sharpe failure — not worth the
additional compute per Step 7 guidance.

**Note for future loops:** the entry condition here (low-volume touch +
confirm-window high-volume reclaim) triggers frequently (~100+ trades
over 8.7yr) but with essentially zero net edge — likely because a
60-day-high "breakout" anchor point is too generic/frequent to represent
a genuinely significant institutional cohort entry (unlike the source's
own intended use case of anchoring to a specific, rare, high-conviction
catalyst like an earnings gap). A future revisit with a stricter/rarer
anchor definition (e.g. a large single-day gap-up, or a much longer
anchor_window like 200 days for a true multi-month breakout) might
better match the source's intended semantics.

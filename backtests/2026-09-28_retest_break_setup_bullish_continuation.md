# Retest & Break Setup Bullish Continuation — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_retest_break_setup_bullish_continuation.py`
**Source:** https://www.luxalgo.com/library/indicator/retest-break-setup/

## Hypothesis

LuxAlgo's "Retest & Break Setup" detects the full breakout-pullback-
continuation sequence: a pivot high breaks, price returns to retest the
broken level (which must hold as support through a required number of
consecutive touches), and a close beyond the retest phase's own highest
high completes the setup — a more disciplined breakout construction than
a naive single-bar pivot break, since it specifically filters out
breakouts that fail immediately.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`pivot_length in {5,10,15}` x `retest_proximity_pct in {1,2,3}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.333 (36/108)** — evenly split 18/54 equity, 18/54 crypto
- by_vol_regime: low 26/36, mid 10/36, high 0/36
- best_cell: SPY, pivot_length=15, retest_proximity_pct=2.0, low-vol, Sharpe 2.43

## Full-sample validators (critical finding)

At the grid's nominal best config (pivot_length=15, retest_proximity_pct=2.0):
QQQ full-sample Sharpe 0.683 (fail), SPY 0.447 (fail). A finer sweep across
all 9 `pivot_length` x `retest_proximity_pct` combinations found NO
setting clears 1.0 Sharpe on either symbol, let alone both simultaneously
— QQQ's best is 0.683, SPY's best is 0.447.

## Decision

**Rejected.** Despite an even, seemingly-robust equity/crypto split in the
grid pass_fraction (0.333, the second-best this cron trigger), full-sample
Sharpe never clears the 1.0 threshold on any parameter setting for either
QQQ or SPY. This is the third strategy this cron trigger (after ROC-of-ROC
and Trading-range Position) to show a decent-looking grid pass rate that
is entirely a low-vol-tercile concentration effect, not a genuine
full-cycle edge.

## Notes for future loops

The retest-and-hold discipline may still be sound in principle (source's
own rationale about liquidity concentration at retested levels is
economically plausible), but this particular mechanical proxy (pivot
lookback + proximity-based retest touch counting) isn't translating into
a full-sample edge. A future loop could try combining this retest logic
with a volume-expansion confirmation (similar to this trigger's Markup &
Markdown attempt) or restrict entries to only the low-vol regime
explicitly (rather than trading unconditionally and hoping the low-vol
tercile dominates), since 26/36 of the passing grid cells were
specifically in that regime.

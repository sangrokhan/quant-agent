# Adam & Eve Double Top Defensive Exit — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_adam_eve_double_top_defensive_exit.py`
**Source:** https://thepatternsite.com/aedt.html

## Hypothesis

Bulkowski's Adam & Eve Double Top: twin peaks that LOOK DIFFERENT (Adam =
narrow/pointed, Eve = wider/rounded), peak variation < 3%, valley drop
>= 10%, confirming when price closes below the valley floor. As a
defensive exit overlay on a plain SMA trend-following long (matching
this repo's UTAD/Pipe Top convention).

## Grid test (Step 6, light workload -- reduced grid)

`validation/grid_test.py::run_strategy_grid`, `trend_window in {30,50}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01.

- **pass_fraction: 0.444 (8/18)**
- by_asset_class: equity 6/12, crypto 2/6
- by_vol_regime: low 6/6, mid 2/6, high 0/6
- best_cell: QQQ, trend_window=50, low-vol, Sharpe 2.71

Follow-up full-sample check across `trend_window in {30,40,50}` found
Sharpe values nearly IDENTICAL to this cron trigger's earlier UTAD/Pipe
Top defensive-exit strategies (QQQ 1.088-1.215, SPY 0.961-1.130,
trend_window=40 clearing both at QQQ 1.088/SPY 1.130). However, a direct
diagnostic check of the pattern-confirmation function itself found this
Adam & Eve detection logic (with its default `peak_tolerance_pct=0.03`,
`min_valley_drop_pct=0.06`, and the Adam/Eve width-asymmetry filter)
confirms only **1 pattern occurrence over the full 2019-2026 QQQ
sample** -- meaning the apparent Sharpe improvement over the plain
SMA(40) baseline is essentially the baseline's OWN performance, not a
genuine test of the Adam & Eve overlay's incremental value. Loosening the
width-asymmetry constraints (adam_width_max=10, eve_width_min=0,
peak_tolerance_pct=0.05) raises confirmations to ~19 over the same
period, but at that point the "looks different" Adam-vs-Eve
distinguishing feature (this pattern's own defining characteristic per
Bulkowski, vs generic double tops already tested) is essentially
discarded.

## Decision

**Rejected — not a genuine test of the hypothesis.** The strategy's
default parameters make the Adam & Eve confirmation event so rare (1
occurrence in 7 years on QQQ) that measured performance is
indistinguishable from the plain SMA(40) baseline already tested via
sibling strategies (UTAD, Pipe Top) -- this doesn't validate or
invalidate the Adam & Eve pattern's specific defensive-exit value, it
just re-measures the baseline. Not worth running the full validator
suite on a signal this degenerate.

## Notes for future loops

The core issue is the "Adam vs Eve, looks different" identification
requirement (Bulkowski's own defining distinction for this
sub-classification vs generic double tops) is hard to operationalize
reliably on daily bars via a simple bar-count width proxy -- it either
fires almost never (strict) or discards the defining feature entirely
(loose). A future loop revisiting this specific Bulkowski
sub-classification should consider a continuous width-ratio score
(Adam_width / Eve_width, thresholded) rather than a binary max/min bar
count, or accept that this repo's existing generic Double Top Setup /
'Big M' strategies already adequately cover the double-top family
without needing the Adam/Eve sub-classification specifically.

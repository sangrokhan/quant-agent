# Shark Harmonic Pattern (0-X-A-B-C) — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_shark_harmonic_pattern.py`
**Source:** https://harmonicsprotrader.com/theoretical-framework/harmonics-theory/shark-pattern/

## Hypothesis

The Shark harmonic pattern (Scott Carney) is a 0-X-A-B-C labelled
reversal pattern (distinct from the classic X-A-B-C-D patterns already
tested in this repo -- Bat/Gartley/Crab/Cypher) that completes at a deep
extension beyond the XA leg (an over-stretched exhaustion point), per the
source's disclosed ratio rules: AB retraces 1.13-1.618x XA; completion at
C is a 1.618-2.24x extension via the BC leg, confluent with an
0.886-1.13x relationship to the 0-X leg. Operationalized as a bullish
0-X-A-B swing-pivot detection + projected-C entry zone, long-only.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`pivot_window in {9,11,15}` x `target_bc_retrace in {0.382,0.5,0.618}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.019 (2/108)**
- by_asset_class: equity 2/54, crypto 0/54
- by_vol_regime: low 0/36, mid 0/36, high 2/36
- best_cell: SPY, pivot_window=11, target_bc_retrace=0.382, high-vol, Sharpe 1.35 (isolated cell)

Follow-up full-sample check at the grid's nominal best config
(pivot_window=11, target_bc_retrace=0.382): QQQ Sharpe 0.231 (17 nonzero
trading days over the full 2019-2026 sample), SPY Sharpe 0.744 (6 nonzero
days) -- extremely sparse signal generation and well below the >= 1.0
threshold on both symbols. Not worth running the full validator suite
given how weak and sparse the grid result is.

## Decision

**Rejected.** Grid pass_fraction of 0.019 (2/108, both in an isolated
high-vol tercile cell) indicates no real edge, and the mechanical
0-X-A-B-C swing-pivot proxy generates very few trades overall (both the
swing-pivot detection and the strict simultaneous-ratio-confluence
requirement are highly restrictive on daily bars). Deleting neither the
strategy file nor this report -- both stay as a record of a rejected
attempt.

## Notes for future loops

Unlike this repo's other harmonic patterns (AB=CD accepted, Crab/Cypher
untested-to-acceptance-status here, Bat/Gartley rejected previously), the
Shark's dual-ratio confluence requirement (Rule 2 AND Rule 3
simultaneously) combined with a 4-point 0-X-A-B swing detection appears
too restrictive for a rolling-fractal daily-bar proxy to find enough
qualifying setups. A future loop attempting harmonic patterns should
consider loosening the confluence requirement to an OR rather than AND,
or moving to intraday bars where harmonic patterns are more traditionally
applied, rather than retrying this exact daily-bar mechanical proxy.

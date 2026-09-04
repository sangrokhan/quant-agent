# ATR-Brick Renko + 200-SMA + ADX>25 Gate — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_renko_adx_gated_trend.py`
**Outcome:** REJECTED

## Hypothesis

Direct follow-up to the rejected 2026-09-04-086 (ATR-brick Renko trend
following): that strategy failed with 0/48 passing grid cells in
high-vol regimes and full-sample Sharpe (best 0.806) just short of 1.0.
Per Pomegra.io/FXNX/PyQuantLab's standard ADX filter guidance, gating
entries to require ADX > 25 (only trade "strong trend present"
conditions) should filter out the choppy/high-vol conditions dragging
down the underlying Renko-brick signal, without touching the core
signal logic itself.

Source: Google AI-overview + Pomegra.io/FXNX/PyQuantLab search snippets
(found via `browser_exec`; `web_search` failed repeatedly with a
DDGS/Yahoo TLS connection error).

## Grid test summary (confirm_bricks x adx_threshold, 2 equity + 2
crypto symbols, 3 vol regimes)

- total_cells: 48, passed_cells: 12, **pass_fraction: 0.250 (unchanged
  from the unfiltered -086 version)**
- by_asset_class: equity 12/24, crypto **0/24**
- by_vol_regime: low 8/16, mid 4/16, high **0/16 (still zero)**
- best_cell: QQQ, confirm_bricks=2/adx_threshold=20, mid-vol regime,
  Sharpe 2.00

## Full-sample Sharpe by config (equity only)

| config | QQQ | SPY |
|---|---|---|
| confirm=2, adx>=25 | 0.729 | 0.318 |
| confirm=1, adx>=25 | 0.521 | 0.381 |
| confirm=2, adx>=20 | 0.889 | 0.219 |
| confirm=2, adx>=30 | 0.434 | 0.157 |

(Compare to the unfiltered version's best: QQQ confirm=2, Sharpe 0.806.)

## Decision

**Rejected -- the ADX gate hypothesis did NOT fix the problem, unlike
the successful min-hold-days fix for 2026-09-04-084/-085.** The ADX>25
filter (and even a looser ADX>20) either left the pass_fraction
unchanged (0.25, identical to the unfiltered version) or actively
*reduced* full-sample Sharpe on SPY (0.665 unfiltered -> 0.318 at
adx>=25) by excluding trades that ADX flagged as weak-trend but that
were still profitable and by not fully filtering the choppy high-vol
period (still 0/16 high-vol grid passes). The best config tested
(QQQ, adx>=20) reaches 0.889, an improvement over the unfiltered 0.806
but still short of the 1.0 threshold. Crypto rejected decisively (0/24
grid cells). Not implemented as a live strategy.

**Key finding for future loops:** unlike the KVO min-hold-days fix
(-084 -> -085, which converted a near-miss into a clean accept), this
ADX-gate fix on the Renko strategy did NOT work -- confirming that "add
a standard filter" is not a universally reliable technique and needs to
be validated per-strategy rather than assumed. The Renko strategy's
weakness appears to be more fundamental (the underlying trend signal
itself, not merely whipsaw noise around a good signal) -- a genuinely
different strategy construction, not a parameter/filter tweak, would be
needed to salvage it.

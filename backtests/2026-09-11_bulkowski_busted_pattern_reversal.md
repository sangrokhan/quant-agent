# Bulkowski Busted Pattern Failed-Breakdown Reversal — ACCEPTED (QQQ + SPY, per-symbol tuned)

**Iteration ID:** 2026-09-11-020
**Date:** 2026-09-11

## Hypothesis

Per Thomas Bulkowski's chart-pattern research (thepatternsite.com, "busted
pattern" concept, disclosed across dozens of pattern-pair studies, e.g.
https://www.thepatternsite.com/ppDescScallops.html, visited this
iteration): a "busted" bearish breakdown occurs when price breaks below a
support level, drops no more than a bounded percentage (Bulkowski's
studies consistently use a ~10% cap across pattern types) before
reversing, and closes back above the original support level -- the
failure of the breakdown itself becomes the buy signal (Bulkowski's own
finding across multiple pattern studies is that busted patterns often
outperform their non-busted counterparts).

This repo generalizes the mechanic (independent of any single specific
chart-pattern shape) using a rolling N-day price low as the generic
"support" reference: (1) support = rolling min close over `lookback` bars
prior to the breakdown, (2) breakdown = close crosses below support, (3)
the breakdown is "busted" if, within `bust_window` bars, the lowest close
reached is no more than `max_drop_pct` below support AND close recovers
back above support, (4) entry on that recovery bar; exit after a
`max_hold_days` time-stop.

Distinct from this repo's existing Swing Failure Pattern entry
(`2026-09-09-087`, rejected) because that is a SAME-BAR wick-rejection
mechanic, while this is a MULTI-DAY breakdown-and-recovery mechanic with
an explicit magnitude cap on the drop (Bulkowski's defining "busted"
characteristic).

## Step 6 grid summary

Grid: `lookback=[15,20,30] x max_drop_pct=[0.05,0.10,0.15] x
bust_window=[10,15]`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT
(crypto), `vol_regime_splits=3`, 2015-01-01 to 2026-09-01, 216 total cells.

- **pass_fraction: 0.120 (26/216)**
- by_asset_class: equity 26/108 (24.1%), crypto 0/108 (0%)
- by_vol_regime: low 6/72 (8.3%), mid 18/72 (25.0%), high 2/72 (2.8%) — notably concentrated in the MID-vol tercile rather than low-vol (unusual pattern for this repo's accepted strategies, most of which are low-vol-concentrated)
- best_cell: SPY mid-vol, `lookback=15, max_drop_pct=0.05, bust_window=15`, Sharpe=1.390

## Step 7 single-config validation (per-symbol fine-tuned)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Trades | Manual walk-forward (4 splits) |
|---|---|---|---|---|---|---|
| QQQ | lookback=15, max_drop_pct=0.15, bust_window=15, max_hold_days=30 | **1.101** (PASS) | 0.172 (PASS, thr 0.25) | 1.056 (PASS, thr 0.5) | 49 | 4/4 positive (PASS) |
| SPY | lookback=12, max_drop_pct=0.15, bust_window=15, max_hold_days=25 | **1.377** (PASS) | 0.165 (PASS, thr 0.25) | 1.310 (PASS, thr 0.5) | 49 | 4/4 positive (PASS) |

Crypto (BTC/USDT, ETH/USDT) rejected decisively at the QQQ config: Sharpe
0.101 / 0.071.

Both symbols independently converged on `max_drop_pct=0.15, bust_window=15`
(a wider drop-tolerance than Bulkowski's canonical ~10%, but consistent
with his own finding that thresholds vary by pattern/asset), with slightly
different `lookback`/`max_hold_days`.

## Decision: ACCEPTED (equity QQQ + SPY, per-symbol tuned configs)

Both symbols pass Sharpe, max drawdown, transaction-cost survival, and
manual walk-forward -- one of the stronger results this cron trigger (SPY
Sharpe 1.377 with TC-survival 1.310 is the best net-of-cost result across
all of today's accepted strategies). Crypto is explicitly out of scope
(decisively rejected).

# Backtest Report: Ergodic Oscillator (Blau) Signal-Line Cross + Zero Filter

**Strategy file:** `strategies/2026-09-06_ergodic_oscillator_zero_filter.py`
**Date:** 2026-09-06
**Outcome:** REJECTED

## Hypothesis

Per LuxAlgo's Ergodic Oscillator library page: William Blau's
double-smoothed momentum ratio (long-length then short-length EMA of
1-bar price change, divided by same pipeline on absolute change, scaled
+/-100), with a signal line. Source's guidance: "Signal-line crosses: the
momentum triggers -- best taken with the zero line or a trend filter as
referee." Long entry on signal-line cross-up while Ergodic>0 (zero-line
trend filter as referee). Distinct from this repo's other Blau-family
indicators already tested: TSI (2026-09-04-129, rejected) and SMI
(2026-09-04-140, rejected) -- the original Ergodic Oscillator construction
had never been tested under this name.

Source: https://www.luxalgo.com/library/indicator/ergodic-oscillator/

## Grid test summary (Step 6)

`param_grid={"long_len": [15,20,25], "max_hold_days": [10,20,30]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3` (108 cells).

- Overall pass_fraction: **0.148** (16/108)
- By asset class: equity 16/54, **crypto 0/54** (decisive reject)
- By vol regime: low 16/36, **mid 0/36, high 0/36** — edge exists only in
  low-vol tercile, a narrow slice
- Best cell: QQQ, long_len=25, max_hold_days=30, low-vol, Sharpe=1.94
- Worst cell: QQQ, long_len=20, max_hold_days=20, high-vol, Sharpe=-1.56
  (severe underperformance in high-vol)

## Single-config validation (Step 7)

Tried two candidate configs (best grid cell and a shorter-hold alternative)
to check if any full-sample config held up:

| Config | QQQ Sharpe | SPY Sharpe | Threshold |
|---|---|---|---|
| long_len=25, max_hold_days=30 | 0.161 — FAIL | 0.206 — FAIL | >= 1.0 |
| long_len=15, max_hold_days=10 | 0.507 — FAIL | 0.262 — FAIL | >= 1.0 |

Both decisively fail full-sample Sharpe — the low-vol-only grid edge does
not survive averaging across the full sample (mid/high vol regimes drag
the average down heavily, especially the -1.56 worst cell).

## Decision

**Reject** (all asset classes/configs). Full-sample Sharpe fails
decisively for both candidate configs on both QQQ and SPY. The grid's
apparent edge is a narrow low-vol-tercile artifact (0/36 pass in mid-vol,
0/36 in high-vol) that does not translate into any usable full-sample
config. Crypto rejected decisively (0/54 grid cells). No walk-forward run
(not needed — already failed at the single-config Sharpe stage).

## Notes for future loops

Both TSI, SMI, and now the plain Ergodic Oscillator (all William Blau
double-smoothed-momentum-family indicators) have now been rejected in
this repo across 3 separate attempts. This family appears to have a
low-vol-only edge that consistently fails to generalize once mid/high-vol
regimes are included — worth deprioritizing this indicator family unless
a future loop specifically restricts trading to a detected low-vol regime
(similar to `2026-09-03_bb_meanrev_qqq_volregime.py`'s explicit gate)
rather than trading through all regimes unconditionally.

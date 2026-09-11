# TPS Connors Scale-In — Front-Loaded Weight Schedule Variant

**Date:** 2026-09-11
**Strategy file:** `strategies/2026-09-11_tps_connors_scalein_frontloaded.py`
**KB id:** 2026-09-11-098

## Hypothesis

Direct follow-up to flagged-for-revisit near-miss 2026-09-06-185 (TPS Connors
scale-in, QQQ Sharpe 0.871, MDD 0.070, param-sens 0.086, WF 4/4 — rejected
by a narrow Sharpe margin). Its notes suggested trying different scale-in
weight schedules. A prior iteration (2026-09-06-186) tried a back-loaded
steeper schedule (10/25/35/50) and made things worse. This iteration tries
the unexplored opposite direction: front-loaded (40/30/20/10) — commit more
size at initial entry, since 2026-09-06-185's own grid found the edge
concentrated in high-vol regimes where a sharp V-bounce may be missed by
waiting to scale in on further weakness.

## Grid test

param_grid = `{rsi_entry_threshold: [20,25], rsi_exit_threshold: [65,70]}`,
QQQ/SPY + BTC/ETH, vol_regime_splits=3, 2018-2026-09. 48 cells.

- pass_fraction: **0.1875** (9/48) — better than original (0.146) and both
  prior schedule variants
- by_asset_class: equity 9/24, crypto 0/24
- by_vol_regime: low 5/16, mid 0/16, high 4/16 (spans both low and high vol,
  same unusual pattern as the parent strategy)
- best cell: rsi_entry=25, rsi_exit=65, QQQ, low-vol, Sharpe 1.81

## Single-config validators (rsi_entry_threshold=25, rsi_exit_threshold=65)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.610 FAIL | 0.427 FAIL |
| Max Drawdown (<=0.25) | 0.084 PASS | 0.123 PASS |
| TC survival (net Sharpe>=0.5) | 0.115 FAIL | -0.097 FAIL |
| Walk-forward (>=0.75) | 1.0 (4/4) PASS | 0.75 (3/4) PASS |
| Parameter sensitivity (<=0.5) | 0.110 PASS | 0.115 PASS |

## Outcome: REJECTED

Full-sample Sharpe (0.610 QQQ / 0.427 SPY) is actually **worse** than the
original balanced-schedule parent (0.871 QQQ), not better — despite the
higher grid pass_fraction (a narrow-slice artifact, same pattern seen
across the repo). Transaction-cost survival also fails decisively (224-250
trades over the sample vs the original's presumably fewer full-size
entries — front-loading to 40% initial size appears to trigger more
partial round-trips that don't reach full conviction before reversing,
raising turnover without raising average P&L per trade).

## Conclusion for this line of research

Both the back-loaded (2026-09-06-186, worse) and front-loaded (this entry,
worse) alternate weight schedules underperform the original balanced
10/20/30/40 schedule (2026-09-06-185). The original design appears to
already be close to a local optimum for the scale-in weighting itself; a
future loop revisiting this near-miss should look at *other* levers (entry
trigger strictness, trend filter window, max_hold_days cap) rather than
further scale-in schedule tweaks, which this and the prior follow-up both
show move performance in the wrong direction from either end.

# Rolling Volume Profile VAH Breakout — Backtest Report (ACCEPTED, SPY only)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_volume_profile_vah_breakout.py`
**Knowledge base id:** 2026-09-08-129

## Hypothesis

Per LuxAlgo's Volume Profile concept explainer
(https://www.luxalgo.com/library/concept/volume-profile/), a rolling N-day
volume profile identifies the Value Area (VA, band holding 70% of the
window's volume around its Point of Control). Price breaking decisively
above the Value Area High (VAH) moves into a low-volume "rejection" shelf
above accepted price levels — "low-volume shelves between nodes are where
price tends to travel fastest" — a breakout-continuation entry. This is
the direct opposite-direction construction from the already-tested
Volume Profile POC/VAL mean-reversion strategy (2026-09-04-150) using the
identical rolling volume-profile machinery, isolating whether direction
alone (breakout vs mean-reversion) changes the outcome.

## Grid test summary (validation/grid_test.py)

- Grid: `profile_window` in {15,20,30} × `n_bins`=12, `va_pct`=0.70,
  `max_hold_days`=10 (3 combos) × {QQQ, SPY, BTC/USDT, ETH/USDT} × 3
  vol-regime terciles = 36 cells.
- **pass_fraction: 0.278** (10/36)
- by_asset_class: equity 10/18 passed; **crypto 0/18 (decisive reject)**
- by_vol_regime: low 6/12; mid 3/12; high 1/12
- best_cell: SPY, profile_window=20, low-vol regime, Sharpe 2.01

## Single-config validators (best config: profile_window=20, n_bins=12,
va_pct=0.70, max_hold_days=10)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full-sample) | 0.994 | 1.031 | ≥1.0 | QQQ near-miss FAIL, SPY pass |
| Max drawdown | 0.109 | 0.076 | ≤0.25 | pass both |
| TC survival (net Sharpe, 10bps/trade) | 0.646 | 0.527 | ≥0.5 | pass both |
| Walk-forward (4-quarter, manual fallback) | 1.0 | 1.0 | ≥0.75 | pass both |
| Parameter sensitivity (relative std, profile_window {15,20,30}) | 0.175 | 0.333 | ≤0.5 | pass both |

Num trades: QQQ 145, SPY 142 over 2019-01 to 2026-09.

## Decision: ACCEPTED (SPY only); QQQ near-miss; crypto rejected decisively

SPY passes all five validators at the grid's best full-grid config
(profile_window=20). QQQ narrowly misses the Sharpe threshold (0.994 vs
1.0) despite passing every other validator — a genuine near-miss worth a
future revisit (e.g. slightly wider `n_bins` or `va_pct` sweep specifically
for QQQ). Crypto (BTC/USDT, ETH/USDT) shows 0/18 grid-cell passes — no edge
whatsoever, consistent with most breakout-family strategies in this
knowledge base failing on crypto's higher noise/24-7 structure.

Kept live in `strategies/` scoped to SPY only per this repo's convention
for single-symbol accepts (cf. 2026-09-08-053, 2026-09-08-073, etc.).

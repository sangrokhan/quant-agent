# Rounding Bottom Neckline Breakout — Backtest Report (REJECTED)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_rounding_bottom_neckline_breakout.py`
**Knowledge base id:** 2026-09-08-131

## Hypothesis

Per https://www.tradingsim.com/blog/rounding-bottom, a rounding bottom
(saucer) is a U-shaped reversal confirmed via a quadratic (parabola)
least-squares fit to closes (positive curvature + R² ≥ threshold), with a
neckline breakout entry, stop at the pattern's MIDPOINT (source's own stated
rule), and a measured-move target (neckline + pattern height). Distinct
from the only other saucer-family strategy in this repo (Cup-and-Handle,
2026-09-06-172, which requires a post-recovery handle pullback) since a
rounding bottom is a direct neckline breakout with no handle.

## Grid test summary (validation/grid_test.py)

- Grid: `pattern_window` in {30,40,50} × `min_r2` in {0.4,0.5},
  `breakout_lookback`=10, `max_hold_days`=30 (6 combos) × {QQQ, SPY,
  BTC/USDT, ETH/USDT} × 3 vol-regime terciles = 72 cells.
- **pass_fraction: 0.236** (17/72)
- by_asset_class: equity 17/36; **crypto 0/36 (decisive reject)**
- by_vol_regime: low 12/24; mid 5/24; **high 0/24**
- best_cell: QQQ, pattern_window=40/min_r2=0.4, low-vol regime, Sharpe 2.52

## Single-config validators (best config: pattern_window=40, min_r2=0.4,
breakout_lookback=10, max_hold_days=30)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full-sample) | 0.814 | 0.373 | ≥1.0 | **FAIL both** |
| Max drawdown | 0.247 | 0.249 | ≤0.25 | pass both (both very close to cap) |
| TC survival (net Sharpe, 10bps/trade) | 0.770 | 0.309 | ≥0.5 | QQQ pass, SPY fail |
| Walk-forward (4-quarter, manual fallback) | 0.75 | 0.75 | ≥0.75 | pass both |
| Parameter sensitivity (relative std, 6-combo grid) | 0.062 | 0.291 | ≤0.5 | pass both |

Num trades: QQQ 31, SPY 33 over 2019-01 to 2026-09.

## Decision: REJECTED

Full-sample Sharpe fails decisively on SPY (0.373) and misses on QQQ (0.814).
The grid's isolated low-vol-regime edge (Sharpe up to 2.52) does not survive
full-sample averaging across regimes — max drawdown is also right at the
0.25 cap on both symbols, an additional red flag. Crypto rejected decisively
(0/36 grid cells). Consistent with the repeated pattern in this knowledge
base where chart-pattern strategies concentrate edge narrowly in low-vol
regimes without holding up broadly.

# Range-Band + IBS Regime Mean Reversion — Backtest Report (REJECTED)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_range_band_ibs_regime_meanrev.py`
**Knowledge base id:** 2026-09-08-133

## Hypothesis

Per https://www.quantitativo.com/p/a-mean-reversion-strategy-with-211
("A Mean Reversion Strategy with 2.11 Sharpe"), the author's own verified
rule: lower band = rolling 10-day High minus 2.5x the rolling 25-day mean
(High-Low) range; long entry when close < lower band AND IBS < 0.3; exit
when close > yesterday's high; gated by a 300-day SMA bull-regime filter
(source's own tested improvement, reducing max drawdown from -24.7% to
-11.7% on their own QQQ backtest). Distinct from every other IBS-family
strategy in this repo via its specific rolling-band construction and
next-bar-high recovery exit.

## Full-sample parameter sweep (before grid test)

Manual sweep of `band_mult` in {2.0,2.5,3.0} × `regime_window` in
{150,200,300} on both QQQ and SPY, full-sample Sharpe:

| band_mult | regime_window | QQQ Sharpe | SPY Sharpe |
|---|---|---|---|
| 2.0 | 150 | 0.622 | 0.484 |
| 2.5 | 150 | 0.611 | 0.688 |
| 3.0 | 150 | 0.519 | 0.778 |
| 2.0 | 300 | 0.571 | 0.565 |
| 2.5 | 300 | 0.547 | 0.770 |
| 3.0 | 300 | 0.452 | **0.806** |

Best full-sample result across the entire sweep: SPY at band_mult=3.0,
regime_window=300, Sharpe 0.806 — still well short of the 1.0 threshold.

## Grid test summary (validation/grid_test.py)

- Grid: `band_mult` in {2.5,3.0} × `regime_window` in {150,300},
  `range_window`=25, `band_window`=10, `ibs_max`=0.3 (4 combos) × {QQQ,
  SPY, BTC/USDT, ETH/USDT} × 3 vol-regime terciles = 48 cells.
- **pass_fraction: 0.188** (9/48)
- by_asset_class: equity 9/24; **crypto 0/24 (decisive reject)**
- by_vol_regime: low 6/16; mid 2/16; high 1/16
- best_cell: QQQ, band_mult=2.5/regime_window=300, low-vol regime, Sharpe
  1.756 (isolated)

## Decision: REJECTED

No parameter combination across a systematic sweep pushes full-sample
Sharpe above ~0.81 on either equity symbol (best: SPY 0.806, still below
the 1.0 threshold). This may reflect a longer/different backtest window
than the source's own 1993-2024 verification run (this repo's data starts
2019), or the source's own author-disclosed shortening of returns after
adding the regime filter (their own write-up: "the total return was almost
cut by half"). Given the grid's decisive fail (0.188 pass_fraction, 0/24 on
crypto) and no full-sample config clears 1.0, this is a clean reject; the
remaining validator suite (TC-survival, walk-forward, parameter
sensitivity) was skipped per Step 7's minimum-subset guidance.

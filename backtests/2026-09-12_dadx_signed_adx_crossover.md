# Backtest Report: Harrington Dynamic ADX Histogram (DADX) Signed-ADX Crossover

**Strategy file:** `strategies/2026-09-12_dadx_signed_adx_crossover.py`
**Date:** 2026-09-12

## Hypothesis

Per Neil Jon Harrington's "Revisualizing The ADX Oscillator" (TASC December
2024 Traders' Tips, fully disclosed Pine v5 source:
https://www.tradingview.com/script/8i1HxfZL-TASC-2024-12-Dynamic-ADX-Histogram/):
a signed-ADX oscillator (DADX = +ADX when DMI+ >= DMI-, else -ADX)
preserves both trend strength and direction in one number, unlike
Wilder's classic unsigned ADX. The source discloses only the visualization
(no trading rule); this strategy tests the natural signal implied by the
construction: long entry when DADX crosses above a low threshold
(genuine, strengthening upward trend), exit on cross back below.

## Grid test (Step 6) — `grid_result_dadx_signed.json`

Grid: `adx_length ∈ {10,14,20}`, `adx_thresh_lo ∈ {15,20,25}` × symbols
{QQQ, SPY, BTC/USDT, ETH/USDT} × vol regime terciles, 2018-01-01 to
2026-09-01. 108 total cells.

- **pass_fraction: 0.2407** (26/108)
- by_asset_class: equity 26/54, **crypto 0/54** (decisive fail)
- by_vol_regime: low 17/36, mid 9/36, **high 0/36**
- best_cell: QQQ, `adx_length=14, adx_thresh_lo=15`, low-vol, Sharpe 2.60
- worst_cell: QQQ, `adx_length=20, adx_thresh_lo=20`, high-vol, Sharpe -1.61

## Full-sample sweep (2018-2026) around the grid's promising region

| Symbol | adx_length=10,thresh=15 | 14,15 | 14,20 | 20,15 |
|---|---|---|---|---|
| SPY | 0.849 | 0.808 | 0.285 | 0.013 |
| QQQ | 0.706 | 0.710 | 0.650 | 0.730 |

No parameter combination reaches the 1.0 Sharpe threshold on the full
2018-2026 sample for either symbol -- the grid's promising per-regime cells
(Sharpe 2.6+) are concentrated entirely in cherry-picked low-vol windows
and do not persist across the full sample including 2020/2022 stress
periods.

## Decision

**REJECT for all symbols/asset classes.** Best full-sample Sharpe achieved
is SPY at 0.849 (adx_length=10, adx_thresh_lo=15), still below the 1.0
threshold; QQQ tops out around 0.73. Did not proceed to the full validator
suite (Sharpe fails decisively across the explored region for both
symbols). Crypto rejected decisively at the grid stage (0/54).

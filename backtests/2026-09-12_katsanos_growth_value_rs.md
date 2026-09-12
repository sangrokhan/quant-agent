# Backtest Report: Katsanos Growth/Value Switching System (Single-Leg RS+VFI Adaptation)

**Strategy file:** `strategies/2026-09-12_katsanos_growth_value_rs.py`
**Date:** 2026-09-12

## Hypothesis

Per Markos Katsanos' "Growth Or Value?" (TASC December 2023 Traders' Tips,
summarized at https://www.tradingview.com/scripts/tasc/page-2/): the
market cycles between favoring growth (VUG) and value (VTV) equities. A
rotation system uses relative strength vs SPY to pick the current leader,
gated by a Volume Flow Indicator (VFI) money-outflow filter. Since this
repo's grid harness tests one symbol at a time, this strategy is a
single-leg adaptation: does holding VUG (or VTV) specifically, per the
RS+VFI signal, produce a genuine edge on that ETF alone (rather than the
source's own fully-rotated two-leg system).

## Manual full-sample sweep (2015-2026) before grid test

VUG best config (rs_window=40, ma_window=60): Sharpe 0.905. VTV best
config (rs_window=10, ma_window=40): Sharpe 0.702. Neither symbol reaches
1.0 across 10 tested parameter combinations.

## Grid test (Step 6) — `grid_result_katsanos_growth_value.json`

Grid: `rs_window ∈ {20,40}`, `ma_window ∈ {40,60}` × symbols {VUG, VTV,
BTC/USDT, ETH/USDT} × vol regime terciles, 2015-01-01 to 2026-09-01.
48 total cells.

- **pass_fraction: 0.0833** (4/48) — weak
- by_asset_class: equity 4/24, **crypto 0/24** (decisive fail)
- by_vol_regime: **low 4/16, mid 0/16, high 0/16**
- best_cell: VUG, `rs_window=20, ma_window=60`, low-vol, Sharpe 2.43
- worst_cell: VUG, `rs_window=20, ma_window=40`, high-vol, Sharpe -0.02

Note: the crypto cells (and technically VTV, since `symbol_hint` isn't
passed by the grid harness and defaults to "VUG") don't get a meaningful
pair-rotation comparison -- this is a known scope limitation of the
single-leg adaptation, documented rather than hidden.

## Decision

**REJECT for all symbols/asset classes.** Best full-sample Sharpe achieved
(VUG, rs_window=40/ma_window=60) is 0.905, still below the 1.0 threshold.
The grid's low-vol-tercile promise (Sharpe 2.43) is a repeat of the
now-familiar pattern in this cron trigger's iterations: attractive
per-regime cells that don't survive the full sample. Weak grid
pass_fraction (0.083) also reflects both the single-leg adaptation's
inherent limitation (missing the source's actual two-way rotation
mechanic) and the approximate RS/VFI formulas used (source's exact custom
indicators weren't fully disclosed in the accessible overview text).
Crypto rejected decisively (0/24).

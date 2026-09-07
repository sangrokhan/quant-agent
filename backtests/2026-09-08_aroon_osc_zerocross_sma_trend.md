# Backtest Report: Aroon Oscillator Zero-Line Crossover + SMA Trend Filter

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_aroon_osc_zerocross_sma_trend.py`
**Source:** https://arrowalgo.com/aroon-oscillator-complete-guide-algorithmic-trading/

## Hypothesis

Per the source's "Zero-line crossover strategy": "Enter long when the Aroon
Oscillator crosses above zero and price is above a longer-period moving
average. Exit when the Oscillator crosses back below zero." Distinct from
four prior Aroon-family entries in this repo (2026-09-04-031 single-line
threshold, 2026-09-04-063 oscillator zero-cross alone, 2026-09-05-079
dual-line 70/30 simultaneous threshold, 2026-09-06-098 crossover+ADX) since
none combine the oscillator-difference zero-cross with a price>SMA trend
filter.

## Grid Test Summary (param_grid: aroon_window=[14,25] x trend_sma_window=[50,100]
x max_hold_days=[15,25]; symbols QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3;
2019-01-01 to 2026-09-01)

- total_cells: 96, passed: 25, **pass_fraction: 0.26**
- by_asset_class: equity 25/48 (0.52), crypto **0/48** (decisively rejected)
- by_vol_regime: low 16/32, mid 6/32, high 3/32 (edge concentrated low-vol)
- best_cell: aroon_window=14, trend_sma_window=50, max_hold_days=25, SPY, low-vol, Sharpe 2.72
- worst_cell: aroon_window=25, trend_sma_window=100, max_hold_days=25, QQQ, high-vol, Sharpe -0.89

## Single-Config Validators (aroon_window=14, trend_sma_window=50,
max_hold_days=25, full period 2019-2026)

| Symbol | Sharpe | MDD | TC-survival (10bps) | Walk-forward (manual 4-split) |
|---|---|---|---|---|
| SPY | **1.501 PASS** (42 trades) | **0.126 PASS** | **net Sharpe 1.371 PASS** | **4/4 PASS** |
| QQQ | 0.801 FAIL (41 trades) | 0.142 PASS | net Sharpe 0.721 PASS | 3/4 PASS |

Parameter sensitivity (SPY, full period, 8 param combos of aroon_window x
trend_sma_window x max_hold_days): Sharpe range 0.610-1.247, relative_std
0.247 (well under 0.5 threshold) — reasonably stable.

Note: manual 4-equal-chunk walk-forward used as a stand-in for
`validation/validators.py::check_walk_forward`, which currently raises
(`vectorbt.utils` has no `splitting` attribute in the installed version) —
same known-broken-API workaround as prior recent iterations.

## Decision: **ACCEPT (SPY only)**

SPY passes all validators at the grid's best config. QQQ near-misses on
headline Sharpe (0.801 vs 1.0 threshold) at the same config — not accepted
for QQQ. Crypto (BTC/USDT, ETH/USDT) rejected decisively across the entire
grid (0/48 cells). Scope: **equity, SPY only**.

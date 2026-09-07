# Backtest Report: Standard Deviation Channel (Regression Line) Pullback Continuation

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_sdc_regression_pullback_continuation.py`
**Source:** https://www.lumleytrading.com/standard-deviation-channels/

## Hypothesis

Per the source's "Trend Continuation at the Regression Line": "In a steeply
ascending channel, the regression line... often acts as dynamic support.
When price pulls back to the regression line in a strong uptrend, this is
often a high-probability long entry." Distinct from 3 prior
regression/SD-channel entries in this repo (SMA20 mean-reversion,
band-breakout, SE-bands width-filter) -- this is the first to trade a
pullback TO the regression line itself.

## Grid Test Summary (param_grid: reg_window=[20,30] x
min_slope_pct=[0.001,0.002] x pullback_tolerance=[0.01]; symbols
QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3; 2019-01-01 to 2026-09-01)

- total_cells: 48, passed: 9, **pass_fraction: 0.1875**
- by_asset_class: equity 9/24, crypto **0/24**
- by_vol_regime: low 8/16, mid 1/16, high 0/16 -- edge concentrated low-vol
- best_cell: reg_window=20, min_slope_pct=0.002, QQQ, low-vol, Sharpe 2.48

## Single-Config Full-Period Check (reg_window=20, min_slope_pct=0.002,
pullback_tolerance=0.01, full period 2019-2026)

| Symbol | Trades | Full-period Sharpe |
|---|---|---|
| QQQ | 85 | 0.544 (decisive FAIL) |
| SPY | 78 | 0.018 (decisive FAIL, essentially no edge) |

Reasonable trade counts (78-85 over 7.7yr, not sparse), clean decisive
rejection on both symbols despite the grid's apparent low-vol-tercile
pass_fraction.

## Decision: **REJECT**

The regression-line-pullback-as-dynamic-support construction does not
produce a usable edge on daily equity/crypto bars -- the low-vol-tercile
grid passes are a narrow-slice artifact that doesn't survive to the full
sample. Crypto rejected 0/24.

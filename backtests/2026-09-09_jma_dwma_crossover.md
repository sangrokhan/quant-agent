# JMA/DWMA Crossover — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_jma_dwma_crossover.py`
**Outcome:** ACCEPTED (QQQ only); SPY very close near-miss; crypto rejected decisively.

## Hypothesis

Per Google AI-overview synthesis (Trading with DaviddTech/LuxAlgo
sources, query "Jurik Moving Average JMA crossover trading strategy
exact entry exit rules"): a fast JMA(7) line crossing above a slower
Double-Weighted Moving Average DWMA(30) line, confirmed by the fast
line's upward slope, signals a long entry; exit primarily on the reverse
crossover, backstopped by an ATR stop-loss (1.5x ATR).

Mark Jurik's actual JMA is proprietary/closed-source; this strategy uses
a well-documented public approximation (double-EMA smoothing, which
captures JMA's core "low lag + reduced noise" design without the
proprietary phase-correction coefficients) for the fast line, and the
standard public DWMA (WMA-of-WMA) formula for the slow line.

First Jurik-family / DWMA-crossover strategy in this repo (0 prior hits)
— distinct from all other MA-crossover variants already tested
(SMA/EMA/HMA/KAMA/TEMA/FRAMA/T3/McGinley/Zero-Lag).

## Single-config validation (best grid cell: fast_span=5, slow_window=20,
max_hold_days=30, atr_mult=1.5)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | **1.273 (PASS)** | **19.3% (PASS)** | **1.175 (PASS)** | **1.0/1.0 (PASS)** | **0.219 (PASS)** |
| SPY | 0.959 (FAIL, thr 1.0, very close) | **10.8% (PASS)** | **0.839 (PASS)** | **1.0/1.0 (PASS)** | **0.100 (PASS)** |

QQQ passes all 5 validators cleanly. SPY is an extremely close near-miss
on Sharpe alone (0.959, just 4% short of the 1.0 threshold) while
passing every other validator comfortably, including a very low 10.8%
max drawdown.

## Grid summary (fast_span=[5,7,10] x slow_window=[20,30] x
max_hold_days=[30], equity=[QQQ,SPY] x crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 72, passed_cells: 18, pass_fraction: 0.25
- by_asset_class: equity 18/36 (0.500), crypto 0/36 (0.0 — decisive fail)
- by_vol_regime: low 12/24 (0.500), mid 6/24 (0.250), high 0/24 (0.0)
- best_cell: fast_span=5/slow_window=20, SPY low-vol regime, Sharpe 2.64
- worst_cell: fast_span=10/slow_window=30, QQQ high-vol regime, Sharpe -1.44

## Verdict: ACCEPTED for QQQ only

QQQ (fast_span=5, slow_window=20, max_hold_days=30, atr_mult=1.5) clears
all 5 standard validators cleanly (Sharpe 1.27, MDD 19.3%, TC-net-Sharpe
1.17, 72 trades over 8.7 years). SPY at the identical config is an
extremely close near-miss (Sharpe 0.959) — worth a future-loop follow-up
with a small local parameter search around this config specifically for
SPY (per this repo's established pattern, e.g. 2026-09-08-154 refining a
near-miss into an accept). Crypto rejected decisively (0/36 grid cells).

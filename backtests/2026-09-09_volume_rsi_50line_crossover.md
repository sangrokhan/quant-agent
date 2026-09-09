# Volume RSI (VoRSI) 50-Line Crossover — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_volume_rsi_50line_crossover.py`
**Outcome:** ACCEPTED (QQQ only); SPY near-miss/rejected; crypto rejected decisively.

## Hypothesis

Per QuantStrategy.io's "How to Trade with Volume RSI Indicator" article:
Volume RSI (VoRSI) applies the classic RSI formula to UP/DOWN VOLUME
instead of up/down price changes: VoRSI = 100 - 100/(1+VoRS), where VoRS
is the ratio of average up-volume to average down-volume over a lookback
window. VoRSI oscillates 0-100 around a 50 midline — above 50 means
bullish volume dominates. Source's exact rule: "buy when the indicator
moves above the 50% line from below and sell when the indicator drops
beneath the 50% line from above."

First Volume RSI (RSI-of-volume-direction) strategy in this repo (0
prior hits) — distinct from OBV/PVT/CMF/MFI which weight price by volume
or vice versa; VoRSI instead computes a pure RSI transform on the
volume series itself, gated by which direction the price moved that day.

## Single-config validation (best grid cell: window=21, max_hold_days=30)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | **1.193 (PASS)** | **21.4% (PASS)** | **1.006 (PASS)** | **1.0/1.0 (PASS)** | **0.131 (PASS)** |
| SPY | 0.882 (FAIL, thr 1.0) | 18.3% (PASS) | 0.684 (PASS) | 1.0/1.0 (PASS) | 0.244 (PASS) |

QQQ passes all 5 validators cleanly. SPY is a near-miss on Sharpe only
(0.882 vs 1.0), passing every other validator.

## Grid summary (window=[7,14,21] x max_hold_days=[10,20,30],
equity=[QQQ,SPY] x crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3,
2018-01-01 to 2026-09-01)

- total_cells: 108, passed_cells: 30, pass_fraction: 0.278
- by_asset_class: equity 30/54 (0.556), crypto 0/54 (0.0 — decisive fail)
- by_vol_regime: low 18/36 (0.500), mid 9/36 (0.250), high 3/36 (0.083)
- best_cell: window=21/max_hold_days=30, SPY low-vol regime, Sharpe 2.59
- worst_cell: window=14/max_hold_days=10, QQQ high-vol regime, Sharpe -0.55

Equity pass rate (55.6%) is the strongest of this run's four candidates
so far, comparable to PVT (52.8%). Crypto rejected decisively.

## Verdict: ACCEPTED for QQQ only

QQQ (window=21, max_hold_days=30) clears all 5 standard validators
cleanly (Sharpe 1.19, MDD 21.4%, TC-net-Sharpe 1.01, 133 trades over 8.7
years). SPY at the identical config is a near-miss (Sharpe 0.88) that
does not clear the bar — kept in `strategies/` as QQQ-scoped only, per
this repo's established per-symbol tuning pattern. Crypto rejected
decisively (0/54 grid cells).

# PVT Signal-Line Crossover (Trend-Filtered) — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_pvt_signal_line_crossover_trend_filtered.py`
**Outcome:** ACCEPTED (QQQ only); SPY near-miss/rejected; crypto rejected decisively.

## Hypothesis

Per Google AI-overview synthesis (Switch Stats/Phemex/StockGro sources,
query "Price Volume Trend PVT indicator strategy exact entry exit
rules"): PVT (a cumulative volume indicator scaling each bar's volume by
that day's percentage price change, unlike OBV's simple +/-full-volume
step) crossing above its own 21-period signal-line SMA while price
trades above a longer-term trend SMA (50 or 200) signals a long entry
(bullish macro trend + PVT-confirmed accumulation), confirmed by a
green (up) candle on the crossover bar. Exit primarily on PVT crossing
back below its signal line, backstopped here by an ATR stop-loss and a
max_hold_days time-stop.

First Price Volume Trend strategy in this repo (0 prior hits on "PVT" /
"Price Volume Trend" in strategies_index.jsonl) — distinct from OBV,
Klinger, Chaikin, and Force Index (different volume-weighting
constructions).

## Single-config validation (best grid cell config: signal_window=30,
trend_window=200, max_hold_days=30, atr_mult=2.5, atr_window=14)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | **1.129 (PASS)** | **13.9% (PASS)** | **0.995 (PASS)** | **1.0/1.0 (PASS)** | **0.129 (PASS)** |
| SPY | 0.549 (FAIL, thr 1.0) | 15.9% (PASS) | 0.366 (FAIL, thr 0.5) | 0.75/1.0 (PASS, borderline) | 0.201 (PASS) |

QQQ passes all 5 validators cleanly. SPY fails Sharpe and TC-survival
(near-miss but not clean) despite passing MDD/walk-forward/param
sensitivity.

## Grid summary (signal_window=[14,21,30] x trend_window=[50,200] x
max_hold_days=[20,30], equity=[QQQ,SPY] x crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 144, passed_cells: 38, pass_fraction: 0.264
- by_asset_class: equity 38/72 (0.528), crypto 0/72 (0.0 — decisive fail)
- by_vol_regime: low 24/48 (0.500), mid 12/48 (0.250), high 2/48 (0.042)
- best_cell: signal_window=30/trend_window=200/max_hold_days=30, QQQ
  low-vol regime, Sharpe 2.42
- worst_cell: signal_window=14/trend_window=200/max_hold_days=20, QQQ
  high-vol regime, Sharpe -0.75

Edge is meaningfully broader than the rejected Fibonacci Time Zone
iteration (equity pass rate 52.8% vs 15.3%), holding up across low and
mid vol regimes on equities, though still weak in high-vol regimes.
Crypto rejected decisively across the entire grid.

## Verdict: ACCEPTED for QQQ only

QQQ (signal_window=30, trend_window=200, max_hold_days=30, atr_mult=2.5)
clears all 5 standard validators cleanly with a healthy 1.13 Sharpe,
13.9% max drawdown, and robust transaction-cost survival at 75 trades
over 8.7 years. SPY at the identical config is a near-miss (Sharpe 0.549)
that does not clear the bar — kept in `strategies/` as QQQ-scoped only;
future loops should NOT assume this generalizes to SPY without a
symbol-specific parameter retune (per this repo's established pattern of
per-symbol tuning, e.g. Chandelier+Supertrend 2026-09-09-090/091).
Crypto rejected decisively (0/72 grid cells) — PVT's volume-percentage
scaling likely doesn't translate well to crypto's more erratic 24/7
volume profile.

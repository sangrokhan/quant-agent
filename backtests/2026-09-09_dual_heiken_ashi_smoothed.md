# Dual Heiken Ashi Smoothed Trend-Following — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_dual_heiken_ashi_smoothed.py`
**Outcome:** REJECTED

## Hypothesis
Per ForexMT4Indicators' Dual Heiken Ashi strategy
(https://forexmt4indicators.com/dual-heiken-ashi-forex-trading-strategy/),
the "Heiken Ashi Smoothed" indicator double-EMA-smooths the Heikin-Ashi
close series. A fast (period ~6) and slow (period ~50) smoothed-HA pair:
long entry when fast is above slow, slow is bullish-colored (established
uptrend), and fast just flipped from bearish to bullish (fresh trigger).
Exit on fast crossing back below slow, fast turning bearish, or a
max_hold_days time-stop. Distinct from 3 prior raw-Heikin-Ashi strategies
in this repo (2026-09-04-045, 2026-09-05-051, 2026-09-05-081), none of
which double-EMA-smooth the HA candles into a dual fast/slow trend system.

## Grid test summary (fast_period x [4,6,10], slow_period x [30,50], max_hold_days x [15,20], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 144, passed_cells: 32, **pass_fraction: 0.222**
- by_asset_class: equity 32/72 (0.444), crypto 0/72 (0.0, decisive fail)
- by_vol_regime: low 24/48, mid 8/48, high 0/48 (concentrated in low-vol equity)
- best_cell: SPY, fast_period=4, slow_period=50, max_hold_days=15, low-vol regime, Sharpe 2.261
- worst_cell: QQQ, same config, high-vol regime, Sharpe -1.253

## Full-sample checks at plausible best configs

| Symbol | fast_period | slow_period | max_hold_days | Full-sample Sharpe | Trades |
|---|---|---|---|---|---|
| QQQ | 4 | 50 | 15 | 0.477 | 157 |
| QQQ | 6 | 50 | 15 | 0.666 | 124 |
| QQQ | 4 | 30 | 15 | 0.656 | 152 |
| QQQ | 10 | 50 | 20 | 0.834 | 90 |
| SPY | 4 | 50 | 15 | 0.534 | 147 |
| SPY | 6 | 50 | 15 | 0.506 | 123 |
| SPY | 4 | 30 | 15 | 0.563 | 145 |
| SPY | 10 | 50 | 20 | 0.557 | 96 |

All full-sample Sharpe values fall short of the 1.0 threshold; best is
QQQ at fast_period=10/slow_period=50/max_hold_days=20 (0.834, still a clear
miss). The grid's low-vol-tercile-only outperformance (24/48 low, 8/48 mid,
0/48 high) does not translate into a full-sample edge once high-vol periods
are included.

## Decision: REJECTED

Grid pass_fraction 0.222 looks superficially promising but is entirely
concentrated in the low-vol tercile; full-sample Sharpe fails on both
equity symbols at every plausible config (best 0.834, still short of 1.0);
crypto decisively rejected 0/72. Not accepted -- consider a future
volatility-regime-gated revisit (restrict entries to low-vol conditions
only, following the pattern of other regime-gated accepts in this repo)
if this angle is revisited.

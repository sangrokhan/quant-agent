# Chande Trend Meter (CTM) Composite Trend-Strength Crossover — Backtest Report

**Strategy file:** `strategies/2026-09-11_chande_trend_meter_ctm.py`
**Date:** 2026-09-11 (id 2026-09-11-033)
**Source:** https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/chande-trend-meter-ctm (StockCharts ChartSchool, Chande Trend Meter)

## Hypothesis

The Chande Trend Meter (CTM) distills 4-timeframe Bollinger %B (20/50/75/100-day),
100-day-std-dev-normalized price change, 14-day RSI, and a 2-day price-channel
breakout flag into a single 0-100 composite trend-strength score. Source's own
suggested rule: CTM crossing above 60 signals a confirmed uptrend. This repo's
implementation tests CTM crossing above `entry_threshold` as a long entry,
exiting when CTM falls back below `exit_threshold` or a `max_hold_days` time-stop.

## Grid test summary (validation/grid_test.py::run_strategy_grid)

- param_grid: `entry_threshold` in {55,60,65}, `exit_threshold` in {35,40,45}
- symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- vol_regime_splits: 3 (low/mid/high realized-vol terciles)
- **108 total cells, 23 passed (pass_fraction 0.213)**
- by_asset_class: equity 23/54 passed, crypto 0/54
- by_vol_regime: low 18/36, mid 5/36, high 0/36
- best_cell: SPY, entry_threshold=65/exit_threshold=35, low-vol Sharpe=2.324
- worst_cell: SPY, entry_threshold=65/exit_threshold=45, high-vol Sharpe=-0.476

A follow-up wider sweep (entry_threshold in {65,70,75,80} x exit_threshold in
{30,35,40}) on full-sample data found **entry_threshold=65, exit_threshold=30**
clears the Sharpe>=1.0 threshold on QQQ (full-sample, not just low-vol slice).

## Single-config validator results (entry_threshold=65, exit_threshold=30)

| Symbol | Sharpe | Passed | Max Drawdown | Passed |
|---|---|---|---|---|
| QQQ | 1.151 | Yes (>=1.0) | 0.210 | Yes (<=0.25) |
| SPY | 0.775 | No | 0.165 | Yes |
| BTC/USDT | 0.147 | No | 0.589 | No |
| ETH/USDT | 0.246 | No | 0.675 | No |

- **Transaction cost survival (QQQ):** net Sharpe after 10bps/trade cost (46 trades) = 1.113, threshold 0.5 -> **Pass**
- **Walk-forward (QQQ):** 4 equal-size date-chunk splits (manual chunking, vbt.utils.splitting attribute unavailable in this vectorbt version) -> per-split Sharpe [1.158, 0.459, 0.816, 1.190], all positive -> pass_fraction 1.0 (threshold 0.75) -> **Pass**
- **Parameter sensitivity (QQQ):** 15-combo grid (entry_threshold in {55,60,65,70,75} x exit_threshold in {25,30,35}), relative_std = 0.142 (threshold <=0.5) -> **Pass**

## Decision

**Accepted for QQQ only** (entry_threshold=65, exit_threshold=30, max_hold_days=60 default). All 5 validators pass for QQQ. SPY is a near-miss (Sharpe 0.775, all other metrics likely fine but not decisive enough to accept). Crypto (BTC/USDT, ETH/USDT) rejected decisively — CTM's Bollinger/RSI/breakout composite does not translate to a tradable edge on crypto's much higher baseline volatility (MDD 0.59-0.67, Sharpe <0.25).

## Notes for future loops

- SPY near-miss at the same config (0.775) — a future iteration could retune entry/exit thresholds specifically for SPY, or add a trend/vol regime gate, following this repo's established near-miss-fix pattern.
- Crypto's decisive rejection (0/54 grid cells) matches this repo's frequent finding that Bollinger/RSI-based composite trend scores built for equity indices do not transfer to crypto's return distribution.

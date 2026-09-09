# Backtest report: Ulcer Index slope (de-stressing) trend-following entry

**Strategy file:** `strategies/2026-09-10_ulcer_index_slope_trend.py`
**Knowledge base id:** 2026-09-10-045
**Outcome: REJECTED** (near-miss; crypto 0/108 decisive; no config clears 1.0 Sharpe on both QQQ and SPY)

## Hypothesis

Per arrowalgo.com's Ulcer Index guide (visited this iteration,
https://arrowalgo.com/ulcer-index-complete-guide-algorithmic-trading/): the
Ulcer Index (UI, RMS of pct drawdown from rolling peak) is a downside-only
drawdown-depth-and-duration metric, and the source emphasizes reading UI's
SLOPE as much as its level ("a falling UI in a rising market means drawdown
stress is clearing -- a positive sign for longs"). This is distinct from
the repo's prior static-threshold UI strategy (2026-09-04-144, fixed "UI
below entry_threshold" level check). Operationalized: long when
close>SMA(trend_window) AND UI has been falling over the trailing
ui_slope_window bars (destressing); exit on UI turning back up, trend
break, or a time-stop.

## Grid test summary (Step 6)

`run_strategy_grid`, param_grid = ui_window∈{10,14,20} ×
ui_slope_window∈{3,5,10} × trend_window∈{50,100}, symbols = {equity:
QQQ/SPY, crypto: BTC/USDT/ETH/USDT}, vol_regime_splits=3, 2018-01-01 to
2024-12-31.

- **total_cells:** 216
- **passed_cells:** 39
- **pass_fraction:** 0.181
- **by_asset_class:** equity 39/108; **crypto 0/108 (decisive fail)**
- **by_vol_regime:** low 24/72, mid 11/72, high 4/72
- **best_cell:** ui_window=20, ui_slope_window=5, trend_window=50, SPY, low-vol tercile, Sharpe=2.158

## Full-sample single-config sweep (Step 7 prep)

| ui_window | slope_window | trend_window | QQQ Sharpe | SPY Sharpe | BTC Sharpe | ETH Sharpe |
|---|---|---|---|---|---|---|
| 20 | 10 | 100 | 1.114 | 0.936 | 0.223 | 0.291 |
| 10 | 5 | 100 | 0.928 | 0.964 | 0.095 | 0.045 |
| 20 | 10 | 50 | 1.063 | 0.836 | 0.170 | 0.230 |

**Best joint config (ui_window=20, ui_slope_window=10, trend_window=100):
QQQ Sharpe=1.114, SPY Sharpe=0.936** — QQQ clears 1.0, but SPY misses by
0.064. No parameter combination in the swept grid clears 1.0 jointly on
both symbols. Crypto is decisively out of scope (best BTC Sharpe found was
only 0.324, at a config that fails equity anyway).

## Decision

**Rejected — near-miss.** No config jointly clears the 1.0 Sharpe threshold
on both QQQ and SPY; the closest (ui_window=20, ui_slope_window=10,
trend_window=100) has QQQ at 1.114 (pass) but SPY at 0.936 (0.064 miss).
Crypto is decisively out of scope. Worth a future fine parameter sweep
around ui_window∈{15,18,20,25}, ui_slope_window∈{7,8,10,12} if revisited,
but not accepted as-is.

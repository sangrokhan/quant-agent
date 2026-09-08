# Standalone Chandelier Exit Trend-Flip Breakout — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_chandelier_exit_trendflip.py`
**Outcome:** REJECTED

## Hypothesis
Per Quantum Algo's Chandelier Exit guide, the Chandelier Exit is an
ATR-based trailing stop (long_stop = Highest(High,period) -
multiplier*ATR(period), ratcheting up only). This strategy treats a close
crossing back ABOVE the Chandelier long_stop line (fresh trend-flip) as the
entry TRIGGER itself, rather than using Chandelier merely as a filter for a
separate signal (already tested: 2026-09-04-035, Chandelier+StochRSI,
rejected). Exit on close crossing back below the line or a max_hold_days
time-stop.

## Grid test summary (period x [14,22], multiplier x [2.0,3.0], max_hold_days x [15,20,30], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 144, passed_cells: 45, **pass_fraction: 0.313** (best grid result of this cron trigger)
- by_asset_class: equity 45/72 (0.625), crypto 0/72 (0.0, decisive fail)
- by_vol_regime: low 24/48, mid 12/48, high 9/48 (broadest vol-regime spread seen this trigger -- not concentrated in only one tercile)
- best_cell: SPY, period=14, multiplier=2.0, max_hold_days=15, low-vol regime, Sharpe 2.298

## Full-sample checks at plausible best configs

| Symbol | period | multiplier | max_hold_days | Full-sample Sharpe | Trades |
|---|---|---|---|---|---|
| QQQ | 14 | 2.0 | 15 | 0.785 | 139 |
| QQQ | 22 | 3.0 | 20 | 0.807 | 105 |
| QQQ | 22 | 2.0 | 15 | 0.810 | 128 |
| SPY | 14 | 2.0 | 15 | 0.734 | 140 |
| SPY | 22 | 2.0 | 15 | **0.815** | 123 |
| SPY | 14 | 3.0 | 30 | 0.755 | 120 |

Best full-sample Sharpe across both symbols and all tested configs is 0.815
(SPY, period=22/multiplier=2.0/max_hold_days=15) -- still short of the 1.0
threshold despite the grid's promising pass_fraction and vol-regime spread.

## Decision: REJECTED

Despite the best grid pass_fraction of this cron trigger (0.313) and a
genuinely broad vol-regime spread (not concentrated in a single tercile
like most other tested strategies), full-sample Sharpe fails on both
equity symbols at every tested config (best 0.815, a real near-miss);
crypto decisively rejected 0/72. This is the closest near-miss of the
cron trigger and a strong candidate for a future refinement (e.g. a
trend/momentum confirmation filter to cut whipsaw trades in choppy
periods, or a tighter multiplier for faster-reacting stops) rather than
abandoning the angle entirely.

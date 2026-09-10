# Backtest Report: AO Twin Peaks with Disclosed Stop/Take-Profit Mechanics

**Strategy file:** `strategies/2026-09-10_ao_twin_peaks_disclosed_stop_takeprofit.py`
**Date:** 2026-09-10

## Hypothesis

Per https://tradingstrategyguides.com/bill-williams-awesome-oscillator-strategy/
(read via `browser_exec` this iteration; `web_search` DDGS backend failed 3x
this cron trigger with TLS/connection errors), the AO Twin Peaks bullish
setup's full 6-step rule set: (1) AO below zero, (2) two swing lows with the
second higher than the first, (3) green bar after the second low, (4) entry
only on a CONFIRMED zero-line break (not merely "ticking up"), (5) stop-loss
placed exactly below the price bar of the SECOND swing low, (6) take-profit
as soon as AO prints two consecutive red bars. This is mechanically distinct
from this repo's already-rejected generic AO Twin Peaks (`2026-09-04-160`,
which used "AO ticking up" as the entry trigger and a trend-break/time-stop
exit rather than the source's own disclosed price-based stop and
oscillator-momentum take-profit).

## Grid test summary (`validation/grid_test.py::run_strategy_grid`)

- Grid: `swing_window` [3,5,7] x `trend_window` [150,200] x `max_hold_days` [20,40,60]
- Symbols: equity [QQQ, SPY], crypto [BTC/USDT, ETH/USDT]
- vol_regime_splits=3, period 2019-01-01 to 2026-09-01
- **Total cells: 216, passed: 24, pass_fraction: 0.111**
- by_asset_class: equity 24/108, crypto 0/108 (decisive crypto rejection)
- by_vol_regime: low 18/72, mid 6/72, high 0/72 (edge concentrated in low-vol tercile only)
- best_cell: swing_window=3/trend_window=150/max_hold_days=20, SPY, low-vol tercile, Sharpe 1.611
- worst_cell: swing_window=3/trend_window=200/max_hold_days=20, QQQ, low-vol tercile, Sharpe -1.183

## Single-config validator results (full sample, swing_window=3, trend_window=200, max_hold_days=40)

| Symbol | Sharpe | Passed | Max Drawdown | Passed | # non-zero-return days |
|---|---|---|---|---|---|
| SPY | 0.612 | FAIL (< 1.0) | 0.033 | passed | 80 |
| QQQ | -0.353 | FAIL (< 1.0, negative) | 0.074 | passed | 59 |

## Decision: REJECT

The grid's 24/216 passing cells are ALL confined to isolated low/mid-vol
tercile slices on equity only (crypto decisively 0/108), and even the
best-performing config's FULL-SAMPLE Sharpe (SPY 0.612, QQQ -0.353) falls
well short of the 1.0 threshold -- the tercile-level near-passes do not
survive aggregation across the whole sample. Max drawdown passes comfortably
on both symbols, but Sharpe is the binding constraint. Not a near-miss;
decisive rejection at the primary-config level despite the more precise
disclosed stop/take-profit mechanics (vs. the prior AO Twin Peaks variant)
failing to meaningfully improve on it.

Strategy file retained as a record of a rejected attempt; not live.

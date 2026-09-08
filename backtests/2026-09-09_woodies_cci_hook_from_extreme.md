# Woodie's CCI Hook From Extreme (HFE) Reversal — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_woodies_cci_hook_from_extreme.py`
**Outcome:** REJECTED

## Hypothesis
Per MarketBulls' Woodies CCI guide (https://market-bulls.com/woodies-cci/),
the "Hook From Extreme" (HFE) pattern is "a reversal signal that occurs
when the CCI hooks within the extreme area after a prolonged trend" -- CCI
dips to/below an extreme threshold (-100 default) then curls upward for
`hook_confirm_bars` consecutive bars while still below zero. Distinct from
already-tested Zero-Line-Reject (2026-09-05-007) and Trendline Break
(2026-09-06-160), both of which operate near the zero line rather than in
the extreme zone. Long entry on hook confirmation; exit on CCI crossing
back above exit_level (0) or a max_hold_days time-stop.

## Grid test summary (extreme_threshold x [-100,-150], hook_confirm_bars x [2,3], max_hold_days x [10,15,20], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 144, passed_cells: 1, **pass_fraction: 0.007** (decisive fail)
- by_asset_class: equity 1/72, crypto 0/72
- by_vol_regime: low 0/48, mid 0/48, high 1/48
- best_cell (single outlier): SPY, extreme_threshold=-150, hook_confirm_bars=2, max_hold_days=15, high-vol, Sharpe 1.119

## Full-sample checks at plausible best configs

| Symbol | extreme_threshold | hook_confirm_bars | max_hold_days | Full-sample Sharpe | Trades |
|---|---|---|---|---|---|
| QQQ | -100 | 2 | 15 | 0.056 | 51 |
| QQQ | -150 | 2 | 15 | 0.128 | 44 |
| QQQ | -100 | 3 | 10 | -0.007 | 39 |
| SPY | -100 | 2 | 15 | 0.250 | 49 |
| SPY | -150 | 2 | 15 | 0.510 | 43 |
| SPY | -100 | 3 | 10 | 0.220 | 35 |

All configs decisively fail the 1.0 Sharpe threshold by a wide margin.

## Decision: REJECTED

Decisive grid failure (pass_fraction 0.007, essentially a single outlier
cell passing out of 144); full-sample Sharpe near zero to weakly positive
across every config on both equity symbols, far short of the 1.0 threshold;
crypto 0/72 decisive. The Hook From Extreme pattern does not show
meaningful edge in this backtest -- not a near-miss worth revisiting.

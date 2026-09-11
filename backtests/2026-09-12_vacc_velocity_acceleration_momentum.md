# VAcc (Velocity + Acceleration Momentum) — Backtest Report

**Date:** 2026-09-12
**Strategy file:** `strategies/2026-09-12_vacc_velocity_acceleration_momentum.py`
**Source:** TASC November 2023 Traders' Tips (Scott Cong, "VAcc: A Momentum
Indicator Based On Velocity And Acceleration"), via
https://www.tradingview.com/scripts/tasc/page-2/

## Hypothesis

For each bar, velocity V(i)=(C-C(i))/i averaged over a lookback window and
EMA-smoothed; acceleration Acc(i)=(V-V(i))/i averaged over the same window
(unsmoothed). Source's own rule: "Strong Upward" = velocity rising AND
acceleration rising above zero (long entry); "Strong Downward" = velocity
falling AND acceleration falling below zero (exit/flat).

## Best config (from grid search)

`lookback=14, velocity_smooth=3` (max_hold_days=30 default)

## Single-config validator results (2018-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass | Param sensitivity (rel. std) |
|---|---|---|---|---|---|
| QQQ | **0.478 (FAIL, thr 1.0)** | **26.2% (FAIL, thr 25%)** | **0.235 (FAIL, thr 0.5)** | 4/4 (pass) | 0.281 (pass, thr 0.5) |
| SPY | 1.089 (pass, thr 1.0) | 16.5% (pass, thr 25%) | 0.697 (pass, thr 0.5) | 4/4 (pass) | 0.356 (pass, thr 0.5) |

QQQ fails 3 of 5 validators (Sharpe, MDD, TC-survival); SPY passes all 5.

## Grid-test summary (2019-01-01 to 2026-09-01)

Grid: `lookback in {7, 10, 14} x velocity_smooth in {3, 5, 8}`, symbols
`{QQQ, SPY} x {BTC/USDT, ETH/USDT}`, vol_regime_splits=3. 108 total cells.

- Overall pass_fraction: 0.231 (25/108)
- By asset class: equity 25/54 passed; **crypto 0/54 passed (decisive reject)**
- By vol regime: low 18/36, mid 5/36, high 2/36
- Best cell: SPY, lookback=14/velocity_smooth=3, low-vol, Sharpe 2.04
- Worst cell: QQQ, lookback=7/velocity_smooth=3, high-vol, Sharpe -0.64

## Decision: ACCEPT (SPY only) / REJECT (QQQ, crypto)

SPY passes all 5 validators. QQQ's higher volatility/trade frequency (239
trades vs SPY's 209 over the same window) erodes the edge after costs and
into a full-sample MDD breach -- this strategy is scoped to SPY only.
Crypto is decisively rejected across the whole grid.

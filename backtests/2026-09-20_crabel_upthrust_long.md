# Toby Crabel "Up Thrust" traded LONG — Backtest Report

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_crabel_upthrust_long.py`
**Source:** https://statoasis.com/overfit/research/unveiling-toby-crabel-s-up-down-thrust-trading-patterns (Ali Casey, StatOasis, 17,424-backtest study)

## Hypothesis

Crabel's up thrust (pivot-high bar, later bar opens above the pivot high,
closes below the previous two closes, closes in the lower half of its own
range -- visually a failed-breakout/bearish-looking candle) is the source's
own headline construction: buy the next open, hold a fixed bar count. The
source measured only a small incremental edge over a random-entry control
on this pattern (1,182 events, +0.39% avg 10-bar return vs +0.29% market
average; random control beat it on 4/8 markets) -- flagged as a
deliberately marginal/skeptical hypothesis, not a strong-edge claim.

## Grid test summary (Step 6)

96 cells: `pivot_left∈{4,10} × max_hold_days∈{10,20} × use_rsi_exit∈{True,False}`
on equity {QQQ,SPY} and crypto {BTC/USDT,ETH/USDT}, 3 vol-regime terciles,
2019-01-01 to 2026-09-01.

- **pass_fraction: 0.469 (45/96)** — surprisingly strong grid result
- by_asset_class: equity 26/48, crypto 19/48 (both nonzero, unusually balanced)
- by_vol_regime: low 17/32, mid 15/32, high 13/32 — evenly spread, not concentrated in one regime tercile alone
- best_cell: pivot_left=4, max_hold_days=20, use_rsi_exit=False, SPY, low-vol, Sharpe 2.44

## Single-config validation (Step 7) — best_cell params, full sample 2019-2026

| Validator | SPY | QQQ | BTC/USDT | ETH/USDT | Threshold |
|---|---|---|---|---|---|
| Sharpe ratio | **FAIL** 0.695 | **FAIL** 0.542 | **FAIL** 0.336 | **FAIL** 0.200 | ≥1.0 |
| Max drawdown | pass 16.5% | pass 14.6% | pass 16.9% | **FAIL** 25.1% | ≤25% |
| Transaction cost survival | pass 0.676 (15 trades) | pass 0.529 (13 trades) | **FAIL** 0.316 (139 trades) | **FAIL** 0.186 (139 trades) | ≥0.5 |
| Walk-forward (4 splits) | pass 0.75 | pass 0.75 | pass 1.0 | pass 0.75 | ≥0.75 |
| Parameter sensitivity | pass 0.153 | pass 0.161 | pass 0.136 | pass 0.157 | ≤0.5 |

## Interpretation

The grid's encouraging 0.469 pass_fraction was again driven by vol-regime
slicing (each tercile is only ~1/3 of the sample) -- full-sample Sharpe
fails on all 4 symbols at the grid's own best_cell config, with crypto
additionally failing transaction-cost survival (139 trades, high turnover)
and ETH/USDT also failing max drawdown. This closely mirrors the pattern
already seen in this cron trigger's down-thrust test (2026-09-20-145) and
several other StatOasis-derived rejections: promising regime-sliced grid
statistics do not survive full-sample validation. Walk-forward passing on
all 4 symbols despite failing Sharpe suggests the strategy is at least
directionally consistent (net positive) across sub-periods, just not with
enough magnitude to clear the Sharpe bar.

## Decision: **REJECTED**

Full-sample Sharpe fails on all 4 symbols (0.20-0.70, all well below the
1.0 threshold); crypto also fails transaction-cost survival and ETH/USDT
fails max drawdown. Consistent with the source's own modest/skeptical
framing of this pattern's edge (marginal over a random-entry control).

# Chande Momentum Oscillator (CMO) Oversold-Reversal — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_cmo_oversold_reversal.py`
**Source:** Google AI-overview synthesis of Quantified Strategies/TradingSim/
GoCharting (web_search failed with a DDGS/Yahoo TLS connection error, fell
back to browser_exec immediately)

## Hypothesis

The Chande Momentum Oscillator (CMO, symmetric -100..+100, distinct
calculation basis from RSI) crossing below an oversold threshold (-50) then
turning back up signals a mean-reversion long entry (gated by price above
200-day SMA), exit on an overbought cross (+50) or a fixed time stop.

## Step 6 — Grid test summary

Grid: `cmo_window` in {9,14} x `oversold_threshold` in {-40,-50} x
`max_hold_days` in {5,10}, symbols {QQQ, SPY} (equity) x {BTC/USDT,
ETH/USDT} (crypto), vol_regime_splits=3.

- **total_cells:** 96, **passed_cells:** 3, **pass_fraction:** 0.031
- **by_asset_class:** equity 3/48, crypto 0/48
- **by_vol_regime:** low 0/32, mid 3/32, high 0/32
- **best_cell:** cmo_window=14, oversold_threshold=-40, max_hold_days=10, QQQ, mid-vol tercile, Sharpe 1.645
- **worst_cell:** cmo_window=9, oversold_threshold=-50, max_hold_days=10, QQQ, low-vol tercile, Sharpe -1.126

Full-sample sweep (4 param combos x 2 symbols):

| Symbol | Params | Sharpe | Trades |
|---|---|---|---|
| QQQ | window=9, os=-50, hold=5 | -0.055 | 47 |
| QQQ | window=14, os=-40, hold=10 | 0.184 | 28 |
| QQQ | window=9, os=-40, hold=5 | -0.309 | 71 |
| QQQ | window=14, os=-50, hold=5 | 0.024 | 18 |
| SPY | window=9, os=-50, hold=5 | -0.119 | 46 |
| SPY | window=14, os=-40, hold=10 | -0.048 | 22 |
| SPY | window=9, os=-40, hold=5 | -0.168 | 69 |
| SPY | window=14, os=-50, hold=5 | 0.183 | 18 |

All 8 full-sample results (4 param combos x 2 symbols) are near-zero to
negative Sharpe (-0.309 to 0.184), decisively below the 1.0 threshold with
no near-miss. Skipped remaining validator suite per Step 7 minimum-subset
guidance (grid pass fraction and full-sample sweep already decisive).

## Decision

**Rejected (all asset classes).** Grid pass_fraction 0.031 (3/96, all in
the mid-vol tercile, none in low/high); full-sample Sharpe never exceeds
0.184 across 8 combo/symbol pairs on equity. Crypto rejected decisively
(0/48 grid cells).

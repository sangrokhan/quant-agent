# Donchian Channel Breakout (Turtle 20/10) — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_donchian_turtle_breakout.py`
**Source:** https://investingpaths.com/tools/backtest/donchian-breakout
(web_extract failed with the recurring DDGS search-only-backend error,
fell back to browser_exec)

## Hypothesis

Per InvestingPaths' Donchian breakout article: the classic 1983 Turtle
Trader system buys at the close on a new 20-day high, and exits on a new
10-day low (asymmetric entry/exit lookback windows). Pure breakout/trend
system, no mean-reversion assumption.

## Step 6 — Grid test summary

Grid: `entry_window` in {20,40,55} x `exit_window` in {10,20}, symbols
{QQQ, SPY} (equity) x {BTC/USDT, ETH/USDT} (crypto), vol_regime_splits=3.

- **total_cells:** 72, **passed_cells:** 18, **pass_fraction:** 0.25
- **by_asset_class:** equity 18/36, crypto 0/36
- **by_vol_regime:** low 12/24, mid 6/24, high 0/24
- **best_cell:** entry_window=55, exit_window=20, SPY, low-vol tercile, Sharpe 2.844
- **worst_cell:** entry_window=55, exit_window=20, SPY, high-vol tercile, Sharpe -0.722

Consistent with this repo's recurring pattern: equity passes, crypto
decisively rejected; low-vol tercile dominant.

Full-sample sweep (4 param combos x 2 symbols):

| Symbol | entry/exit | Sharpe | MDD |
|---|---|---|---|
| QQQ | 20/10 (standard) | 1.240 | 0.178 |
| QQQ | 40/10 | 1.032 | 0.226 |
| QQQ | 55/20 | 0.934 | 0.149 |
| QQQ | 40/20 | 0.914 | 0.277 |
| SPY | 20/10 (standard) | 0.933 | 0.098 |
| SPY | 40/10 | 0.518 | 0.222 |
| SPY | 55/20 | 0.402 | 0.232 |
| SPY | 40/20 | 0.441 | 0.275 |

## Step 7 — Single-config validation (primary config: entry_window=20, exit_window=10, standard Turtle rule, QQQ)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.240 | 1.0 | ✅ |
| Max drawdown | 0.178 | 0.25 | ✅ |
| Transaction cost survival (net Sharpe, 10bps/trade, 64 trades) | 1.144 | 0.5 | ✅ |
| Walk-forward (4 splits, manual date-slice fallback due to vectorbt.utils.splitting API bug) | 1.0 (4/4 positive) | 0.75 | ✅ |
| Parameter sensitivity (relative std across 4 param combos) | 0.126 | 0.5 | ✅ |

## Decision

**Accepted (QQQ only)** at standard Turtle config (entry_window=20,
exit_window=10) — all 5 validators pass cleanly.

**Rejected (SPY)** — best full-sample Sharpe across all 4 tested param
combos is 0.933 (standard 20/10 config itself), never clearing the 1.0
threshold on SPY despite passing on QQQ with identical params (a
QQQ-only-accept pattern also seen elsewhere in this repo, e.g. Force Index
-049, OBV -027, CMF -043, A/D -047).

**Rejected (crypto)** — decisively, 0/36 grid cells passed for BTC/USDT
and ETH/USDT across the full parameter grid.

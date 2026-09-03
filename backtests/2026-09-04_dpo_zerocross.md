# Detrended Price Oscillator (DPO) Zero-Line Cycle Cross — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_dpo_zerocross.py`
**Source:** Google AI-overview synthesis (QuantifiedStrategies' own DPO
article 404'd; TradingView/GoCharting corroborate the core formula/rule)
(web_search failed with a DDGS/Yahoo TLS connection error, fell back to
browser_exec immediately)

## Hypothesis

The Detrended Price Oscillator (DPO = close - a backward-shifted SMA)
isolates cyclical price structure by removing the trend component while
preserving cycle timing -- a fundamentally different construction from
every prior oscillator in this repo. Mechanically-testable simplification
of the source's trough/peak-reversal rule: long entry when DPO crosses
above zero from below, exit when DPO crosses back below zero.

## Step 6 — Grid test summary

Grid: `dpo_window` in {10,20,30}, symbols {QQQ, SPY} (equity) x
{BTC/USDT, ETH/USDT} (crypto), vol_regime_splits=3.

- **total_cells:** 36, **passed_cells:** 10, **pass_fraction:** 0.278
- **by_asset_class:** equity 10/18, crypto 0/18
- **by_vol_regime:** low 6/12, mid 3/12, high 1/12
- **best_cell:** dpo_window=20, SPY, low-vol tercile, Sharpe 2.902
- **worst_cell:** dpo_window=30, QQQ, high-vol tercile, Sharpe -0.579

Full-sample sweep (3 windows x 2 symbols):

| Symbol | dpo_window | Sharpe | MDD | Trades |
|---|---|---|---|---|
| QQQ | 10 | 1.181 | 0.232 | 182 |
| QQQ | 20 | 0.996 | 0.313 | 119 |
| QQQ | 30 | 0.824 | 0.289 | 111 |
| SPY | 10 | 1.256 | 0.122 | 164 |
| SPY | 20 | 1.195 | 0.137 | 107 |
| SPY | 30 | 0.830 | 0.240 | 93 |

## Step 7 — Single-config validation (primary config: dpo_window=10)

### QQQ

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.181 | 1.0 | ✅ |
| Max drawdown | 0.232 | 0.25 | ✅ |
| Transaction cost survival (net Sharpe, 10bps/trade, 182 trades) | 0.906 | 0.5 | ✅ |
| Walk-forward (4 splits, manual date-slice fallback) | 1.0 (4/4 positive) | 0.75 | ✅ |
| Parameter sensitivity (relative std across 3 windows) | 0.146 | 0.5 | ✅ |

### SPY

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.256 | 1.0 | ✅ |
| Max drawdown | 0.122 | 0.25 | ✅ |
| Transaction cost survival (net Sharpe, 10bps/trade, 164 trades) | 0.906 | 0.5 | ✅ |
| Walk-forward (4 splits, manual date-slice fallback) | 1.0 (4/4 positive) | 0.75 | ✅ |
| Parameter sensitivity (relative std across 3 windows) | 0.172 | 0.5 | ✅ |

## Decision

**Accepted (QQQ and SPY)** at dpo_window=10 — all 5 validators pass
cleanly for both equity symbols (a notably strong, dual-symbol accept
compared to several recent QQQ-only or SPY-only accepts in this repo).

**Rejected (crypto)** — decisively, 0/18 grid cells passed for BTC/USDT
and ETH/USDT.

# Choppiness Index (CHOP) Trending-Regime Gate + SMA Trend Filter — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_choppiness_trend_gate.py`
**Source:** https://www.quantifiedstrategies.com/choppiness-index/
(specific numeric trading rules paywalled members-only; web_search failed
with a DDGS/Yahoo TLS connection error, fell back to browser_exec)

## Hypothesis

The Choppiness Index (Bill Dreiss) is a non-directional 0-100 regime
classifier (low=trending, high=choppy). Since it cannot indicate
direction, this implements a mechanically-testable regime-gated trend
filter: long entry when CHOP(14) < 38 (trending regime) AND close > SMA
trend filter (directional confirmation); exit when CHOP > 62 (regime
shifts choppy) OR the trend filter breaks.

## Step 6 — Grid test summary

Grid: `chop_window` in {14,20} x `trend_window` in {50,100}, symbols
{QQQ, SPY} (equity) x {BTC/USDT, ETH/USDT} (crypto), vol_regime_splits=3.

- **total_cells:** 48, **passed_cells:** 10, **pass_fraction:** 0.208
- **by_asset_class:** equity 10/24, crypto 0/24
- **by_vol_regime:** low 8/16, mid 2/16, high 0/16
- **best_cell:** chop_window=14, trend_window=50, QQQ, low-vol tercile, Sharpe 3.419
- **worst_cell:** chop_window=20, trend_window=50, SPY, high-vol tercile, Sharpe -1.104

Full-sample sweep (4 param combos x 2 symbols):

| Symbol | Params | Sharpe | MDD | Trades |
|---|---|---|---|---|
| QQQ | cw=14, tw=50 | 1.188 | 0.155 | 54 |
| QQQ | cw=14, tw=100 | 0.842 | 0.240 | 61 |
| QQQ | cw=20, tw=50 | 0.890 | 0.241 | 38 |
| QQQ | cw=20, tw=100 | 0.801 | 0.238 | 41 |
| SPY | cw=14, tw=50 | 0.366 | 0.180 | 61 |
| SPY | cw=14, tw=100 | 0.237 | 0.159 | 55 |
| SPY | cw=20, tw=50 | 0.244 | 0.181 | 45 |
| SPY | cw=20, tw=100 | 0.623 | 0.161 | 33 |

## Step 7 — Single-config validation (primary config: chop_window=14, trend_window=50, QQQ)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.188 | 1.0 | ✅ |
| Max drawdown | 0.155 | 0.25 | ✅ |
| Transaction cost survival (net Sharpe, 10bps/trade, 54 trades) | 1.105 | 0.5 | ✅ |
| Walk-forward (4 splits, manual date-slice fallback) | 0.75 (3/4 positive) | 0.75 | ✅ |
| Parameter sensitivity (relative std across 4 combos) | 0.164 | 0.5 | ✅ |

## Decision

**Accepted (QQQ only)** at chop_window=14, trend_window=50 — all 5
validators pass (walk-forward at exactly the 0.75 threshold, 3/4 splits
positive).

**Rejected (SPY)** — best full-sample Sharpe across all 4 combos is 0.623
(chop_window=20, trend_window=100), never clearing the 1.0 threshold.

**Rejected (crypto)** — decisively, 0/24 grid cells passed for BTC/USDT
and ETH/USDT.

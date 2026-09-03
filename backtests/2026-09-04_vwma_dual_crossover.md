# Volume Weighted Moving Average (VWMA) Dual Crossover — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_vwma_dual_crossover.py`
**Source:** Google search snippets (Pineify VWMA Strategy Guide, article
404'd but snippet visible; corroborated by ThinkorSwim's VWMABreakouts)
(web_search failed with a DDGS/Yahoo TLS connection error, fell back to
browser_exec)

## Hypothesis

VWMA (volume-weighted rolling average price, distinct from every other
volume-weighted indicator in this repo which weight a momentum measure by
volume rather than the price average itself) dual crossover: fast (20)
VWMA crossing above slow (50) VWMA signals a long entry; exit on the
opposite cross.

## Step 6 — Grid test summary

Grid: `fast_window` in {10,20} x `slow_window` in {50,100}, symbols
{QQQ, SPY} (equity) x {BTC/USDT, ETH/USDT} (crypto), vol_regime_splits=3.

- **total_cells:** 48, **passed_cells:** 12, **pass_fraction:** 0.25
- **by_asset_class:** equity 12/24, crypto 0/24
- **by_vol_regime:** low 8/16, mid 4/16, high 0/16
- **best_cell:** fast_window=10, slow_window=100, SPY, low-vol tercile, Sharpe 2.665
- **worst_cell:** fast_window=10, slow_window=50, QQQ, high-vol tercile, Sharpe -0.654

Full-sample sweep (4 param combos x 2 symbols):

| Symbol | Params | Sharpe | MDD | Trades |
|---|---|---|---|---|
| QQQ | fw=10, sw=50 | 0.853 | 0.186 | 53 |
| QQQ | fw=10, sw=100 | 1.160 | 0.194 | 23 |
| QQQ | fw=20, sw=50 | 0.933 | 0.303 | 39 |
| QQQ | fw=20, sw=100 | 0.931 | 0.273 | 15 |
| SPY | fw=10, sw=50 | 0.927 | 0.151 | 45 |
| SPY | fw=10, sw=100 | 1.102 | 0.218 | 21 |
| SPY | fw=20, sw=50 | 0.631 | 0.309 | 35 |
| SPY | fw=20, sw=100 | 0.962 | 0.256 | 17 |

## Step 7 — Single-config validation (primary config: fast_window=10, slow_window=100)

### QQQ

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.160 | 1.0 | ✅ |
| Max drawdown | 0.194 | 0.25 | ✅ |
| Transaction cost survival (net Sharpe, 10bps/trade, 23 trades) | 1.135 | 0.5 | ✅ |
| Walk-forward (4 splits, manual date-slice fallback) | 0.75 (3/4 positive) | 0.75 | ✅ |
| Parameter sensitivity (relative std across 4 combos) | 0.118 | 0.5 | ✅ |

### SPY

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.102 | 1.0 | ✅ |
| Max drawdown | 0.218 | 0.25 | ✅ |
| Transaction cost survival (net Sharpe, 10bps/trade, 21 trades) | 1.070 | 0.5 | ✅ |
| Walk-forward (4 splits, manual date-slice fallback) | 0.75 (3/4 positive) | 0.75 | ✅ |
| Parameter sensitivity (relative std across 4 combos) | 0.189 | 0.5 | ✅ |

## Decision

**Accepted (QQQ and SPY)** at fast_window=10, slow_window=100 — all 5
validators pass cleanly for both equities (a low-trade-count strategy,
only 21-23 trades over 7.7yr, benefiting from low transaction-cost drag).

**Rejected (crypto)** — decisively, 0/24 grid cells passed for BTC/USDT
and ETH/USDT.

# Backtest Report: REIT ETF Trading System (Katsanos, simplified daily adaptation)

**Strategy file:** `strategies/2026-09-12_reit_katsanos_rate_gated.py`
**Date:** 2026-09-12

## Hypothesis

Per Markos Katsanos' "Is The Price REIT?" (TASC June 2024 Traders' Tips,
fully disclosed weekly strategy:
https://www.tradingview.com/script/gkp6SIlb-TASC-2024-06-REIT-ETF-Trading-System/):
REIT ETFs (VNQ) are rate-sensitive and market-correlated; a dual entry
system (Bollinger oversold-bounce + Donchian uptrend-breakout), gated by a
10-Year Treasury Yield (^TNX) rate-sensitivity filter (favor entries when
rates are falling/flat), should outperform. This strategy simplifies the
source's weekly multi-condition system into a daily-bar version with the
same core dual-entry + TNX gate + chandelier-stop exit.

## Full-sample sanity check (VNQ, 2015-2026) BEFORE grid test

Multiple parameter combinations on the strategy's own target asset (VNQ)
all produced **negative** full-sample Sharpe: -0.352, -0.433, -0.219,
-0.129, -0.501 across 5 tested configs. This is a strong early signal the
adaptation doesn't work on its intended instrument.

## Grid test (Step 6) — `grid_result_reit_katsanos.json`

Grid: `donchian_window ∈ {30,40,60}`, `tnx_roc_max ∈ {-0.02,0.0,0.05}` ×
symbols {VNQ, QQQ, BTC/USDT, ETH/USDT} × vol regime terciles, 2015-01-01
to 2026-09-01. 108 total cells.

- **pass_fraction: 0.0926** (10/108) — weak
- by_asset_class: equity 10/54, **crypto 0/54** (decisive fail)
- by_vol_regime: low 7/36, mid 3/36, **high 0/36**
- best_cell: QQQ (not VNQ!), `donchian_window=60, tnx_roc_max=0.05`,
  low-vol, Sharpe 1.72 -- notably the target asset VNQ contributed NO
  passing cells in the top result; QQQ (used as a control/comparison
  symbol) accounts for the grid's few passes
- worst_cell: VNQ, `donchian_window=40, tnx_roc_max=0.05`, high-vol,
  Sharpe -0.74

## Decision

**REJECT for all symbols/asset classes**, most decisively for VNQ itself
(the strategy's own intended target) which shows consistently negative
full-sample Sharpe across every tested configuration. The rate-sensitivity
gate + dual Bollinger/Donchian entry construction does not translate well
from the source's weekly-bar, multi-branch original into this daily-bar
simplified adaptation. Did not proceed to the full validator suite given
the decisive full-sample and grid failures. Crypto rejected decisively at
the grid stage (0/54).

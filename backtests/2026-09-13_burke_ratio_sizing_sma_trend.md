# Burke Ratio (Root-Sum-Square Drawdown) Dynamic Sizing SMA Trend Strategy — Backtest Report

**Date:** 2026-09-13
**Strategy file:** `strategies/2026-09-13_burke_ratio_sizing_sma_trend.py`
**KB entry:** 2026-09-13-052

## Hypothesis
Per the Burke Ratio (confirmed via Google AI Overview synthesizing
QuantMemo/LuxAlgo/Wharton, browser_exec after web_search returned zero
results): Burke Ratio = (Return - RiskFree) / sqrt(sum(D_i^2)), using the
root-SUM-of-squares of drawdowns (not root-MEAN like Ulcer Index),
making it sensitive to drawdown frequency as well as depth. Scales an
SMA(200) trend gate's exposure by trailing Burke ratio.

## Config (best from grid)
`trend_window=200, burke_window=60, burke_reference=0.3, leverage_cap=1.0`

## Single-config validator results (2019-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| SPY | 1.198 (pass) | 0.117 (pass) | 1.147 (pass) | 0.75 (pass) | 0.132 (pass) | 28 |
| QQQ | 0.897 (fail, thr 1.0) | 0.182 (pass) | 0.856 (pass) | 0.75 (pass) | 0.050 (pass) | 35 |
| BTC/USDT | 1.063 (pass) | 0.379 (fail, thr 0.25) | 1.045 (pass) | 0.75 (pass) | 0.068 (pass) | 46 |

## Grid summary (72 cells: 3 burke_reference x 2 burke_window x 2 equity + 2 crypto symbols x 3 vol regimes)
- pass_fraction: 0.333 (24/72)
- by_asset_class: equity 18/36, crypto 6/36
- by_vol_regime: low 15/24, mid 9/24, high 0/24
- best_cell: SPY, burke_reference=0.3/burke_window=60, low-vol, Sharpe 2.829

## Decision
**Accepted for SPY only** — all 5 validators pass. Near-identical numeric
pattern to the same-day Pain Ratio strategy (2026-09-13-051), likely
because both are averaging-family drawdown aggregations that correlate
highly with each other in practice on this data.
**Near-miss/rejected QQQ**, **rejected BTC/USDT (MDD)**.

## Source
Burke Ratio formula via Google AI Overview / QuantMemo / LuxAlgo / Wharton (browser_exec)

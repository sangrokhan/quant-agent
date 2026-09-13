# Pain Ratio (Zephyr, Average-Drawdown-Based) Dynamic Sizing SMA Trend Strategy — Backtest Report

**Date:** 2026-09-13
**Strategy file:** `strategies/2026-09-13_pain_ratio_sizing_sma_trend.py`
**KB entry:** 2026-09-13-051

## Hypothesis
Per https://breakingdownfinance.com/finance-topics/performance-measurement/zephyr-pain-index/
(Becker/Moore 2006, browser_exec): Pain Index = average drawdown (not
max like MAR-ratio, not RMS like Ulcer Index -- a third distinct
drawdown-aggregation method). Pain Ratio = annualized return / Pain
Index. This strategy scales an SMA(200) trend gate's exposure by trailing
Pain Ratio.

## Config (best from grid)
`trend_window=200, pain_window=60, pain_ratio_reference=3.0, leverage_cap=1.0`

## Single-config validator results (2019-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| SPY | 1.193 (pass) | 0.117 (pass) | 1.143 (pass) | 0.75 (pass) | 0.129 (pass) | 28 |
| QQQ | 0.888 (fail, thr 1.0) | 0.185 (pass) | 0.847 (pass) | 0.75 (pass) | 0.065 (pass) | 35 |
| BTC/USDT | 1.064 (pass) | 0.376 (fail, thr 0.25) | 1.046 (pass) | 0.75 (pass) | 0.068 (pass) | 46 |

## Grid summary (72 cells: 3 pain_ratio_reference x 2 pain_window x 2 equity + 2 crypto symbols x 3 vol regimes)
- pass_fraction: 0.333 (24/72)
- by_asset_class: equity 18/36, crypto 6/36
- by_vol_regime: low 15/24, mid 9/24, high 0/24
- best_cell: SPY, pain_ratio_reference=3.0/pain_window=60, low-vol, Sharpe 2.840

## Decision
**Accepted for SPY only** — all 5 validators pass.
**Near-miss/rejected QQQ** — Sharpe 0.888, all else passes.
**Rejected BTC/USDT** — passes Sharpe but decisive MDD fail (0.376>0.25).

## Source
https://breakingdownfinance.com/finance-topics/performance-measurement/zephyr-pain-index/ (browser_exec)

# Gain-to-Pain-Ratio (Schwager) Dynamic Sizing SMA Trend Strategy — Backtest Report

**Date:** 2026-09-13
**Strategy file:** `strategies/2026-09-13_gain_to_pain_ratio_sizing_sma_trend.py`
**KB entry:** 2026-09-13-050

## Hypothesis
Per Jack Schwager's Gain-to-Pain Ratio (GPR, Market Wizards; formula
confirmed via Google AI Overview/TradesViz/WallStreetMojo, browser_exec
after web_search returned zero results): GPR = sum(all periodic returns)
/ abs(sum(negative periodic returns)). This strategy scales an SMA(200)
trend gate's exposure by the underlying asset's own trailing GPR --
distinct arithmetic (sum-based, all-returns-in-numerator) from every other
sizing overlay tested this cron trigger (inverse-vol, CVaR, MAR-ratio,
downside-deviation, Omega-ratio).

## Config (best from grid)
`trend_window=200, gpr_window=40, gpr_reference=0.8, leverage_cap=1.0`

## Single-config validator results (2019-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| SPY | 0.661 (fail) | 0.107 (pass) | 0.543 (pass) | 0.75 (pass) | 0.224 (pass) | 43 |
| QQQ | 1.083 (pass) | 0.121 (pass) | 0.975 (pass) | 0.75 (pass) | 0.265 (pass) | 54 |
| BTC/USDT | 1.146 (pass) | 0.247 (pass) | 1.114 (pass) | 0.75 (pass) | 0.065 (pass) | 62 |
| ETH/USDT | 0.996 (fail, thr 1.0) | 0.470 (fail) | 0.978 (pass) | 1.0 (pass) | 0.200 (pass) | 52 |

## Grid summary (72 cells: 3 gpr_reference x 2 gpr_window x 2 equity + 2 crypto symbols x 3 vol regimes)
- pass_fraction: 0.431 (31/72) — the highest pass fraction of any strategy
  tested this cron trigger.
- by_asset_class: equity 15/36, crypto 16/36 (roughly balanced, unlike
  every other sizing overlay this trigger which skewed heavily equity)
- by_vol_regime: low 19/24, mid 10/24, high 2/24 (first strategy this
  trigger with ANY high-vol-regime passes)
- best_cell: QQQ, gpr_reference=0.8/gpr_window=40, low-vol, Sharpe 2.700

## Decision
**Accepted for QQQ and BTC/USDT** — both pass all 5 validators cleanly.
This is the first strategy this cron trigger accepted for CRYPTO.
**Rejected SPY** — fails Sharpe (0.661).
**Rejected ETH/USDT** — near-miss Sharpe (0.996) but decisive MDD fail
(0.470).

## Source
Gain-to-Pain Ratio formula via Google AI Overview / TradesViz /
WallStreetMojo (browser_exec, web_search returned zero results for the
direct query).
